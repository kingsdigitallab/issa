# Small Resolution, High FPS: Optimising Programme Boundary Detection

## Summary

To boost fps on long videos, two changes are needed: raise `max_frames` at startup (the hard cap on frame count), and lower the per-request video token budget (which shrinks resolution via `smart_resize`). This document shows how to experiment with different resolution/fps tradeoffs using only `VIDEO_TOKENS` — no YaRN, no FP8, no new infrastructure.

## The Key Insight

### You cannot directly fix the resolution

`smart_resize` has no "fixed resolution" mode. It auto-adjusts based on two inputs:

1. **`longest_edge`** — total pixel volume budget (`num_frames × H × W`)
2. **`num_frames`** — how many frames are sampled

You control the resolution *indirectly* by setting these two values. More frames → smaller frames (same total budget). Fewer tokens → smaller frames.

### `max_frames=768` is the real bottleneck

With the current `max_frames=768`, making the resolution smaller does NOT boost fps. The frame count is capped at 768 regardless of how few tokens the video uses:

```
90min: 768 frames, 0.14 fps, 480x352, 63,360 tokens (under 64K budget)
```

768 frames at 480x352 = 63K tokens — well under the 64K budget. Shrinking to 192x128 would use only ~9K tokens, but the frame count stays 768. The wasted budget does not convert to more frames. **`max_frames` is the cap, not the token budget.**

## The One Startup Change Needed

Add `"max_frames"` to the existing `--mm-processor-kwargs` in `vllm.sh`:

```bash
# Current:
--mm-processor-kwargs '{"size": {"longest_edge": 268435456, "shortest_edge": 4096}}'

# Changed (just adds max_frames):
--mm-processor-kwargs '{"size": {"longest_edge": 268435456, "shortest_edge": 4096}, "max_frames": 5400}'
```

`max_frames=5400` allows 1 fps on 90-min videos (5400 = 5400s × 1 fps). With the default `fps=2`, the processor requests 10,800 frames but `max_frames` clamps to 5400, giving effective 1.0 fps.

For 1.5 fps experiments, use `max_frames=8100` (8100 = 5400s × 1.5 fps).

### Safety of raising max_frames

- Warmup/profiling always uses 2 frames — unaffected
- Encoder cache budget depends on `longest_edge` (not `max_frames`) — unchanged
- The encoder activation is bounded by `longest_edge` (total patches = token budget × 4), not by frame count

## How Resolution Varies With `VIDEO_TOKENS`

The per-request `longest_edge` = `VIDEO_TOKENS × 2048`. Different values give different resolutions at the `max_frames` cap.

### At 5400 frames (90-min videos, 1.0 fps)

| `VIDEO_TOKENS` | longest_edge | Resolution | Video tokens | Total w/ 82K overhead | Fits 256K? |
|----------------|-------------|------------|-------------|-----------------------|------------|
| 64k | 134M | 160x128 | 54K | 136K | Yes |
| **73k-80k** | **153-168M** | **192x128** | **65K** | **147K** | **Yes** |
| 90k | 189M | 192x160 | 81K | 163K | Yes |
| 100k | 210M | 224x160 | 95K | 177K | Yes |
| 128k | 268M | 256x192 | 130K | 212K | Yes |

### At 8100 frames (90-min videos, 1.5 fps — needs `max_frames=8100`)

| `VIDEO_TOKENS` | longest_edge | Resolution | Video tokens | Total w/ 82K overhead | Fits 256K? |
|----------------|-------------|------------|-------------|-----------------------|------------|
| 64k | 134M | 128x96 | 49K | 131K | Yes |
| 90k | 189M | 160x128 | 81K | 163K | Yes |
| **128k** | **268M** | **192x128** | **97K** | **179K** | **Yes** |

## Resolution Varies With Duration

The resolution is only "fixed" for videos that hit the `max_frames` cap. Shorter videos get higher resolution (fewer frames, more budget per frame). Example with `max_frames=5400` and `VIDEO_TOKENS=80k`:

| Duration | Frames | Effective fps | Resolution | Video tokens |
|----------|--------|---------------|------------|-------------|
| 5 min | 600 | 2.0 | 640x480 | ~90K |
| 10 min | 1,200 | 2.0 | 448x320 | ~84K |
| 30 min | 3,600 | 2.0 | 256x192 | ~86K |
| 60 min | 5,400 (clamped) | 1.5 | 192x128 | 81K |
| **90 min** | **5,400 (clamped)** | **1.0** | **192x128** | **81K** |

This is reasonable — shorter videos get better resolution because they have fewer frames to spread the budget across.

## Full Results Tables

### Current setup (max_frames=768, VIDEO_TOKENS=64k, longest_edge=134M)

| Duration | Frames | Effective fps | Resolution | Video tokens |
|----------|--------|---------------|------------|-------------|
| 5 min | 600 | 2.00 | 544x384 | 61,200 |
| 10 min | 768 | 1.28 | 480x352 | 63,360 |
| 30 min | 768 | 0.43 | 480x352 | 63,360 |
| 60 min | 768 | 0.21 | 480x352 | 63,360 |
| 90 min | 768 | 0.14 | 480x352 | 63,360 |

### max_frames=5400, VIDEO_TOKENS=64k (longest_edge=134M)

| Duration | Frames | Effective fps | Resolution | Video tokens |
|----------|--------|---------------|------------|-------------|
| 5 min | 600 | 2.00 | 544x384 | 61,200 |
| 10 min | 1,200 | 2.00 | 384x288 | 64,800 |
| 30 min | 3,600 | 2.00 | 192x160 | 54,000 |
| 60 min | 5,400 | 1.50 | 160x128 | 54,000 |
| 90 min | 5,400 | 1.00 | 160x128 | 54,000 |

### max_frames=5400, VIDEO_TOKENS=90k (longest_edge=189M)

| Duration | Frames | Effective fps | Resolution | Video tokens |
|----------|--------|---------------|------------|-------------|
| 5 min | 600 | 2.00 | 640x480 | 90,000 |
| 10 min | 1,200 | 2.00 | 448x320 | 84,000 |
| 30 min | 3,600 | 2.00 | 256x192 | 86,400 |
| 60 min | 5,400 | 1.50 | 192x160 | 81,000 |
| 90 min | 5,400 | 1.00 | 192x160 | 81,000 |

### max_frames=5400, VIDEO_TOKENS=128k (longest_edge=268M)

| Duration | Frames | Effective fps | Resolution | Video tokens |
|----------|--------|---------------|------------|-------------|
| 5 min | 600 | 2.00 | 768x576 (native!) | 129,600 |
| 10 min | 1,200 | 2.00 | 544x384 | 122,400 |
| 30 min | 3,600 | 2.00 | 288x224 | 113,400 |
| 60 min | 5,400 | 1.50 | 256x192 | 129,600 |
| 90 min | 5,400 | 1.00 | 256x192 | 129,600 |

### max_frames=8100, VIDEO_TOKENS=128k (longest_edge=268M, 1.5 fps target)

| Duration | Frames | Effective fps | Resolution | Video tokens |
|----------|--------|---------------|------------|-------------|
| 5 min | 600 | 2.00 | 768x576 (native!) | 129,600 |
| 10 min | 1,200 | 2.00 | 544x384 | 122,400 |
| 30 min | 2,700 | 1.50 | 320x224 | 113,400 |
| 60 min | 5,400 | 1.50 | 256x192 | 129,600 |
| 90 min | 8,100 | 1.50 | 192x128 | 97,200 |

## Experiment Plan

### Phase 1: Raise max_frames (startup change)

In `vllm.sh`, add `"max_frames": 5400` to `--mm-processor-kwargs`:

```bash
--mm-processor-kwargs '{"size": {"longest_edge": 268435456, "shortest_edge": 4096}, "max_frames": 5400}'
```

No other startup changes. Restart the server.

### Phase 2: Resolution sweep (per-request changes only)

Run `answer_videos_vlm.bash` with different `ANSWER_VIDEOS_VLM_VIDEO_TOKENS` values, no server restart between runs:

| Run | `VIDEO_TOKENS` | 90-min resolution | 90-min fps | Tokens used | Purpose |
|-----|----------------|-------------------|------------|-------------|---------|
| A | 64k | 160x128 | 1.0 | 54K | Most aggressive downscale |
| B | 80k | 192x128 | 1.0 | 65K | Target resolution |
| C | 100k | 224x160 | 1.0 | 95K | Gentle downscale |
| D | 128k | 256x192 | 1.0 | 130K | Mild downscale (baseline) |

Compare detection quality across runs. The sweet spot is where resolution is just enough for the model to recognise programme boundaries (logos, title cards, color shifts) while maximising temporal density.

### Phase 3: 1.5 fps (if 1.0 fps is insufficient)

Restart server with `max_frames=8100`, then run with `VIDEO_TOKENS=128k`:

| Run | `VIDEO_TOKENS` | 90-min resolution | 90-min fps | Tokens used |
|-----|----------------|-------------------|------------|-------------|
| E | 128k | 192x128 | 1.5 | 97K |

If 192x128 at 1.5 fps is too aggressive, try `VIDEO_TOKENS=192k` (longest_edge=393M) — but this exceeds the startup `longest_edge=268M`. The per-request value should not exceed the startup value. To use 192K tokens, the startup `longest_edge` must also be raised (see Phase 4).

### Phase 4: Unlock higher token budgets (optional)

If you need more than 128K video tokens, raise the startup `longest_edge`:

```bash
# 192K encoder budget:
--mm-processor-kwargs '{"size": {"longest_edge": 393216000, "shortest_edge": 4096}, "max_frames": 8100}'
```

This enables per-request `VIDEO_TOKENS` up to 192K. The encoder activation for 192K tokens is ~10.4 GiB (well within the 23.8 GiB headroom at 0.70 utilisation). No OOM risk.

At 8100 frames with 192K tokens:

| `VIDEO_TOKENS` | Resolution | Video tokens |
|----------------|------------|-------------|
| 128k | 192x128 | 97K |
| 192k | 256x192 | ~194K |

## To Truly Fix Resolution for All Videos

The current approach gives different resolutions for different durations (shorter videos get higher resolution). To get exactly 192x128 regardless of duration, framesense.py would need to calculate `longest_edge` per-request based on the actual video duration:

```python
desired_fps = 1.0  # or from operator param
target_w, target_h = 192, 128
num_frames = int(duration_seconds * desired_fps)
longest_edge = num_frames * target_w * target_h
# -> send as mm_processor_kwargs.size.longest_edge
```

This requires a code change in framesense.py. The startup `max_frames` would still need to be raised to allow enough frames through.

## What Does NOT Change

- `--max-model-len 256k` — all configurations fit within 256K
- `--kv-cache-dtype` — stays bf16 (no FP8 needed for these experiments)
- `--gpu-memory-utilization 0.70` — unchanged
- `--skip-mm-profiling` — still needed
- `--media-io-kwargs '{"video": {"num_frames": -1}}'` — still loading all frames
- `--limit-mm-per-prompt '{"image": 0, "video": 1}'` — still one video per request
- `--enable-chunked-prefill --max-num-batched-tokens 8192` — still chunked prefill
