# Controlling FPS and Image Resolution (framesense + vLLM)

This document explains how to actually control the two video-processing values
that matter for the small-resolution / high-fps experiments:

- **fps** — temporal density (how many frames per second are sampled)
- **image resolution** — spatial size of each sampled frame

It is written after discovering (via the diagnostic patch in `vllm-patches/`)
that changing `max_fps` in the framesense request or `max_frames` in the vLLM
launch arguments **had no effect** on the answer and reasoning of the Qwen
model. The reason is a routing problem explained below.

## The key insight: two separate parameter channels in vLLM

vLLM has two independent channels for video parameters:

| Channel | CLI flag | Reaches | Controls |
|---------|----------|---------|----------|
| `mm_processor_kwargs` | `--mm-processor-kwargs` | HF processor (`smart_resize`) | **Resolution** via `size.longest_edge` |
| `media_io_kwargs` | `--media-io-kwargs` | `VideoMediaIO` → `Qwen3VLVideoBackend` | **Frame sampling**: `fps`, `num_frames`, `max_frames` |

The two values you care about travel on different channels:

- **Resolution** travels on `mm_processor_kwargs` — this is why `VIDEO_TOKENS`
  already works.
- **fps** and `max_frames` are read during frame sampling by
  `Qwen3VLVideoBackend.compute_frames_index_to_sample`, which only sees the
  `media_io_kwargs` channel.

### The bug

framesense currently sends `fps` and `max_frames` inside
`mm_processor_kwargs` (the HF processor channel). Because the video loader
never reads that channel, the settings are dropped and the defaults are used
instead:

- `fps = 2` (default in `Qwen3VLVideoBackend.load_bytes`)
- `max_frames = 768` (default in `compute_frames_index_to_sample`)

That is why no combination of `ANSWER_VIDEOS_VLM_MAX_FPS` (0.1, 0.5, 1, 2) or
launch `max_frames` (768, 5400, 8100) changed anything — none of them reached
the frame sampling code, which kept clamping to `fps=2` / `max_frames=768`.

## Where framesense builds the request

In `/home/jeff/src/prj/tools/framesense/operators/base/operator.py`
(around line 852), the video options are constructed:

```python
video_processor_options = {
    "fps": float(self.get_param('max_fps', 2)),          # from ANSWER_VIDEOS_VLM_MAX_FPS
    "size": {
        "longest_edge": self.get_byte_size(self.get_param('video_tokens', '12k')) * 2048,  # from VIDEO_TOKENS
        "shortest_edge": 4096,
    },
    "max_frames": 8100,                                  # hardcoded
}
```

- `fps` comes from the operator parameter `max_fps`, overridable via
  `ANSWER_VIDEOS_VLM_MAX_FPS` (default `2.0`).
- `longest_edge` comes from the operator parameter `video_tokens` via
  `ANSWER_VIDEOS_VLM_VIDEO_TOKENS`, scaled by `2048`
  (`temporal_patch_size * patch_size^2 * merge_size^2 = 2 * 16^2 * 2^2`).
- `max_frames` is hardcoded to `8100`.

The whole `video_processor_options` dict is sent as `mm_processor_kwargs` in
the request, so `fps` and `max_frames` go to the wrong channel.

## How to control each value

### Resolution (already works)

Set `ANSWER_VIDEOS_VLM_VIDEO_TOKENS`. It flows through
`mm_processor_kwargs.size.longest_edge` to the HF `smart_resize`. Smaller token
budgets → smaller frames.

| `VIDEO_TOKENS` | `longest_edge` |
|----------------|----------------|
| 12k            | 25,165,824 |
| 64k            | 134,217,728 |
| 128k           | 268,435,456 |

### FPS and max_frames (currently ignored, need a fix)

These must reach the **media_io_kwargs channel** to have any effect. Two ways
to do that:

1. **Per-request in framesense** — send `fps` / `max_frames` in the request's
   `media_io_kwargs.video` instead of (or in addition to) `mm_processor_kwargs`.
   This keeps per-request tuning via env vars and avoids server restarts.

2. **Server-level in vllm.sh** — set them in `--media-io-kwargs`. All requests
   share the value; requires a server restart to change.

## Recommended change to vllm.sh

The operative launch change would be to set frame sampling on the correct
channel:

```bash
--media-io-kwargs '{"video": {"fps": <FPS>, "num_frames": -1, "max_frames": <N>}}'
```

For example, to force 1 fps with up to 8100 frames on 90-minute videos:

```bash
--media-io-kwargs '{"video": {"fps": 1.0, "num_frames": -1, "max_frames": 8100}}'
```

## Full control matrix

| Setting | Where | Channel | Status |
|---------|-------|---------|--------|
| Resolution | `ANSWER_VIDEOS_VLM_VIDEO_TOKENS` | `mm_processor_kwargs.size.longest_edge` | **Works now** |
| FPS | `ANSWER_VIDEOS_VLM_MAX_FPS` | currently `mm_processor_kwargs.fps` (wrong) | **Needs fix** → move to `media_io_kwargs.video.fps` |
| `max_frames` cap | hardcoded `8100` in framesense, or `--media-io-kwargs` in vllm.sh | frame sampling | **Needs fix** → set on `media_io_kwargs` channel |

## How the frame count is actually computed

`Qwen3VLVideoBackend.compute_frames_index_to_sample` (in
`vllm/multimodal/video.py`) is the authoritative frame counter:

```python
num_frames = int(total_frames_num / original_fps * fps)   # fps drives the count
num_frames = min(max(num_frames, min_frames), max_frames, total_frames_num)
```

- `total_frames_num` / `original_fps` = video duration in seconds.
- `fps` = the sampling fps (default `2`).
- The result is clamped to `[min_frames=4, max_frames=768]`.

So the effective fps = `num_frames / duration`. Whenever `fps * duration`
exceeds `max_frames`, the frame count is capped and the effective fps drops.

## Plan options for making fps / max_frames controllable

1. **Patch framesense** — change `video_processor_options` so `fps` /
   `max_frames` are sent as request-level `media_io_kwargs.video` instead of
   (or in addition to) `mm_processor_kwargs`. Minimal, keeps per-request tuning
   via env vars, no server restarts.

2. **Set in vllm.sh only** — put `fps` / `max_frames` in
   `--media-io-kwargs`. Server-level, loses per-request flexibility, requires
   restart to change.

3. **Both** — fix framesense routing *and* set sensible defaults in vllm.sh.

## See also

- `vllm-patches/README.md` — diagnostic patch that prints the actual fps,
  frame count and resolution used at runtime.
- `05-small-res-high-fps.md` — the resolution/fps trade-off experiments.
