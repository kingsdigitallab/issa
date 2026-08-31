# vLLM Diagnostic Patch: Video Processing Trace

Diagnostic-only patches for `vllm-openai_v0.28.0-cu130.sif` that print the
**actual** fps, total frame count and frame resolution vLLM uses when it
processes an input video. No functional behaviour is changed — the patches
only add `logger.warning(...)` output lines.

## Why

When tuning video processing through `max_frames` (vLLM launch args) and `fps`
(request `/` `mm_processor_kwargs`), vLLM may silently ignore them. This patch
reveals the values actually applied, so you can confirm which settings are
being honoured and which are being dropped.

## Files patched

| Patched file (this directory) | Inside the SIF |
|-------------------------------|----------------|
| `vllm/multimodal/video.py` | `/usr/local/lib/python3.12/dist-packages/vllm/multimodal/video.py` |
| `vllm/multimodal/media/video.py` | `/usr/local/lib/python3.12/dist-packages/vllm/multimodal/media/video.py` |

Both files were extracted verbatim from the SIF and then edited. Original,
unpatched files can be re-extracted at any time:

```bash
singularity exec vllm-openai_v0.28.0-cu130.sif \
    cat /usr/local/lib/python3.12/dist-packages/vllm/multimodal/video.py
```

Note: vLLM may also be installed under `/usr/local/lib/python3.12/dist-packages` or
as an editable install; adjust the container paths if your SIF differs.

## What the patches log

### 1. `VideoMediaIO.load_bytes()` — parameters reaching the video loader

```
[VIDEO DEBUG] VideoMediaIO.load_bytes: num_frames=-1, kwargs={} (these go to the video loader backend)
```

Shows what frame-sampling parameters actually reach the video loader backend.
`kwargs` comes from `--media-io-kwargs '{"video": {...}}'`. If `fps` /
`max_frames` are missing here, they were never routed to the loader.

### 2. `Qwen3VLVideoBackend.compute_frames_index_to_sample()` — the framer cap decision

```
[VIDEO DEBUG] Qwen3VLVideoBackend.compute_frames_index_to_sample:
  Source      : total_frames=135000, original_fps=25.0000, duration=5400.00 s
  Parameters  : fps=2.0000 (from target), max_frames=768 (from kwargs, default=768), min_frames=4
  Computed    : num_frames=768 (before clamp: 10800)
  Effective fps: 0.142222
  kwargs received: {}
```

This is the **critical** diagnostic. `fps` and `max_frames` here are read from
the video-loader kwargs, whose defaults are 2 and 768 respectively. If your
requested values do not appear, that proves they are going to the HF processor
channel instead of the video loader channel.

### 3. `VideoBackend.load_bytes()` — decoded output resolution/shape

```
[VIDEO DEBUG] VideoBackend.load_bytes decoded output: frames shape=(768, 576, 768, 3) (N,H,W,C), expected_frames=768, decoded_frames=768, backend=opencv
```

Shows the actual decoded frame array: `N` = number of frames, `H`/`W` = pixel
resolution (before any HF `smart_resize` downsampling).

## How to apply (bind-mount, no SIF rebuild)

The patched files are bound over the originals when launching the container,
so the SIF itself is untouched.

Add two `--bind` flags (and the existing binds) to your `singularity exec`
invocation in `inferencers/vllm.sh`:

```bash
PATCH_DIR=/put/your/absolute/path/to/vllm-patches

singularity exec --nv \
    \
    --bind $PATCH_DIR/vllm/multimodal/video.py:\
        /usr/local/lib/python3.12/dist-packages/vllm/multimodal/video.py \
    --bind $PATCH_DIR/vllm/multimodal/media/video.py:\
        /usr/local/lib/python3.12/dist-packages/vllm/multimodal/media/video.py \
    \
    --bind $COLLECTION_PATH:$COLLECTION_PATH \
    --bind $HF_HOME:$HF_HOME \
    $SING_FILE \
    vllm serve $MODEL_NAME ...
```

Replace `$PATCH_DIR` with the absolute path to this `vllm-patches` directory
(e.g. `/scratch/prj/dh_issa/issa/workshops/ws1/vllm-patches` on the HPC).

**Important:** bind-mount paths must be absolute. Singularity resolves the
host path against the host filesystem, and the container path against the
container. If the server does not pick up the patch (no `[VIDEO DEBUG]` lines),
the paths are likely wrong or relative.

## Reading the output

- Confirm **effective fps** = `num_frames / duration`. If it drops with duration
  for long videos while `fps` stays fixed, `max_frames` is capping you.
- If `Parameters: fps=<your value>` but `max_frames=768` (the default), your
  `fps` change is being applied but `max_frames` is not reaching the loader.
  Fix: move `max_frames`/`fps` into `--media-io-kwargs '{"video": {...}}'`.
- If `Parameters: fps=2` and `max_frames=768` (both defaults), neither of your
  settings reached the loader. Your `fps`/`max_frames` in `mm_processor_kwargs`
  go to the HF processor channel, not the video loader channel.

## Interpreting: two separate parameter channels in vLLM

| Channel | CLI flag | Reaches | Controls |
|---------|----------|---------|----------|
| `mm_processor_kwargs` | `--mm-processor-kwargs` | HF processor (`smart_resize`) | Resolution via `size.longest_edge` |
| `media_io_kwargs` | `--media-io-kwargs` | `VideoMediaIO` → `Qwen3VLVideoBackend` | Frame sampling: `fps`, `num_frames`, `max_frames` |

`fps` and `max_frames` sent inside `mm_processor_kwargs` in the request body
are read by the HF processor (and only matter when `do_sample_frames=True`,
which is off by default). The actual frame sampling in
`Qwen3VLVideoBackend.compute_frames_index_to_sample` reads them only from the
video-loader kwargs, whose defaults are `fps=2` and `max_frames=768`. That is
why changing request `fps` / launch `max_frames` (via `mm_processor_kwargs`) has
no effect.

To change the frame sampling, set them on the video-loader channel instead:

```bash
--media-io-kwargs '{"video": {"fps": 1.0, "num_frames": -1, "max_frames": 8100}}'
```
