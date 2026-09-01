# RAM OOM During Video Decode (90-min, 32K budget, fps=1)

## Summary

A 90-minute video prompted with a **32K vision-token budget** (`longest_edge =
32*1024*2048 = 67,108,864`), `max_frames=8100` and `fps=1` crashes with OOM on
an A100 80G with only **24 GB of host RAM**, despite the small token budget
implying a tiny frame resolution. The VLM tuning analysis (docs 04/05) assumed
this could not happen because it reasoned only about the *VRAM / encoder*
budget. It turns out the OOM is a **host-RAM (system RAM)** failure, caused by
the way vLLM decodes video frames.

## Root cause: decode happens at native resolution, before `smart_resize`

`longest_edge` (and therefore `--video-tokens`) only caps the **output**
resolution that HF's `smart_resize` produces (here 128×96). It does **not** cap
the amount of RAM used to decode and hold the frames *before* resizing.

The sequence at runtime is:

1. `VideoMediaIO.load_file` reads the **entire compressed mp4** into memory
   (`data = f.read()`, up to ~7.4 GB for these sources) and keeps it resident
   in `MediaWithBytes(video, data)` —
   `inferencers/vllm-patches/vllm/multimodal/media/video.py:180`.
2. The video loader decodes the sampled frames at **native source resolution**
   into one host numpy array. With the OpenCV backend (the default, set only
   via `--media-io-kwargs '{"video": {"num_frames": -1}}'` in `vllm.sh`),
   `_read_frames_no_recovery` preallocates
   `np.empty((N, H, W, 3), dtype=np.uint8)` at native 768×576 —
   `inferencers/vllm-patches/vllm/multimodal/video.py:460`.
3. Only afterwards does the HF `smart_resize` shrink every frame to fit the
   token budget (128×96 at 32K, driven by `num_frames`).

So **decode RAM ≈ `num_frames × source_H × source_W × 3` bytes**, independent
of the token budget.

### How `num_frames` is computed for a 90-min video

`Qwen3VLVideoBackend.compute_frames_index_to_sample`
(`inferencers/vllm-patches/vllm/multimodal/video.py:1280-1321`):

```python
num_frames = int(total_frames_num / original_fps * fps)   # int(135000/25*1) = 5400
num_frames = min(max(num_frames, min_frames), max_frames, total_frames_num)
```

For 90 min at 25 fps (135,000 frames): `fps=1 → 5400` frames; `fps=1.5 → 8100`.

### Memory math (source 768×576, uint8)

One frame = `576 × 768 × 3 = 1,327,104` bytes (~1.27 MiB). The whole mp4 is
held resident (~7.4 GB for the largest sources). Total host RAM usage ≈
decoded array + mp4 bytes + the server's own RSS (Python/torch/vLLM engine,
typically several GB).

| 90-min @ fps | `max_frames` | frames | decoded array | + mp4 (7.4 GB) | ≈ peak (incl. server) |
|--------------|--------------|--------|---------------|----------------|-----------------------|
| 0.5          | 8100         | 2700   | 3.6 GB        | 11.0 GB        | ~13–15 GB             |
| **1.0**      | **8100**     | **5400**| **7.2 GB**    | **14.6 GB**    | **~17–19 GB**         |
| 1.5          | 8100         | 8100   | 10.8 GB       | 18.2 GB        | ~21–23 GB (**OOM**)   |

At `fps=1` the peak is right at the edge of 24 GB and gets killed (SIGKILL from
the Linux OOM killer); `fps=1.5` reliably exceeds it. This matches the earlier
"SIGKILL ... OOM killer (system RAM)" observation noted in `vllm.sh` and
docs/04.

## Confirmation steps (from the diagnostic patch)

The debug patch prints the actual decode:

```
[VIDEO DEBUG] VideoBackend.load_bytes decoded output:
  frames shape=(N, H, W, C) (N,H,W,C), expected_frames=N, ...
```

- If `N=5400`: `fps`/`max_frames` **reached the video-loader channel** and the
  RAM math above applies (this is the expected cause of the OOM).
- If `N=768`: `fps`/`max_frames` are still only on the `mm_processor_kwargs`
  channel (the default routing bug in docs/06) and were dropped; then the
  OOM implies the source resolution is much higher than 768×576. Verify the
  source `H×W` in the same log line.

Confirm the actual source resolution before tuning (`H,W` in that line).

## Options

### Option 1 — Resize-during-decode (recommended, proper fix)

Patch `inferencers/vllm-patches/vllm/multimodal/video.py` so each sampled frame
is resized to the final target immediately after it is decoded, **before** it
accumulates in RAM. Peak RAM then drops to `num_frames × small_res × 3` (e.g.
5400 × 128×96 × 3 ≈ 200 MB), independent of the native source resolution.

- Effort: moderate — the loader must know the target resolution. That requires
  `longest_edge` (or an explicit target W×H) to be passed on the
  `--media-io-kwargs` / loader channel (currently it lives on the
  `mm_processor_kwargs` channel and is invisible to the loader). The target per
  frame can be derived from `num_frames` and `longest_edge` the same way
  `smart_resize` does.
- Trade-off: preserves 1–1.5 fps; the most robust solution; a bit of invasive
  loader code, plus keeping the target in sync with the HF processor.

### Option 2 — Free the mp4 bytes early (small, quick win)

Patch `media/video.py` to release the full compressed `data` bytes as soon as
decode completes (instead of holding them in `MediaWithBytes`). Frees up to
~7.4 GB of host RAM, enough to fit 5400 frames within 24 GB.

- Effort: ~5 lines.
- Trade-off: keeps 5400 frames but with less safety margin than Option 1; does
  not reduce the decoded-array cost at 8100 frames (fps=1.5 still OOMs).

### Option 3 — Both (maximum safety margin)

Combine Option 1 and Option 2 for a very low, predictable host-RAM footprint
(mp4 bytes freed + only resized frames held). Best if you want headroom for
8100 frames / fps=1.5 without touching infra.

### Option 4 — Config-only (no code)

Lower `max_frames` (and/or fps) so the decoded array fits 24 GB, e.g.
`max_frames≈2700` → 3.6 GB decoded array → ~14 GB peak.

- Effort: none (just launch/request values).
- Trade-off: caps 90-min videos at ≤0.5 fps, which conflicts with the ≥1 fps
  goal for programme-boundary detection. Only suitable as a temporary check.

### Alternatives

- **Pre-downsample on disk**: transcode the source clips to a compact proxy
  (lower spatial res and/or a fixed low frame count) so the loader decodes a
  small input. Offloads the heavy lifting but adds a pre-processing step and
  extra storage.
- **Add host RAM**: not possible on this shared cluster/slurm node (24 GB
  fixed); listed for completeness.

## Recommendation

1. First confirm from the debug log the actual `N` and source `H×W` (steps
   above) — this verifies whether `fps`/`max_frames` are routed correctly.
2. Implement **Option 3 (resize-during-decode + free mp4 bytes)** for a robust,
   predictable host-RAM footprint that supports fps=1.5 on 90-min videos.
   If invasive changes are undesirable, start with **Option 2** (quick) which
   gets 5400 frames (fps=1) within 24 GB, then evaluate Option 1 if you need
   fps=1.5.

## See also

- `inferencers/vllm-patches/README.md` — diagnostic patch and the two
  parameter channels (`media_io_kwargs` vs `mm_processor_kwargs`).
- `docs/06-control-fps-res.md` — how to route fps / max_frames / resolution.
- `docs/04-vram_video_context_analysis.md`, `docs/05-small-res-high-fps.md` —
  prior VRAM-only analysis (did not account for decode-time host RAM).
- `vllm/multimodal/video.py:1280-1321` (frame counting), `:451-536`
  (frame reading / allocation), `video.py:180` (mp4 bytes held resident).
