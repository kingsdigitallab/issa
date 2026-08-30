# Capping Resolution to Increase FPS for Long Videos

## The Problem

Programme boundary detection requires sufficient temporal density (fps) to catch short visual separators (logos, title cards, color shifts). But `max_frames=768` caps the frame count regardless of video duration, so a 90-min video gets only 0.14 fps — far too low for reliable detection.

## The Mechanism

`longest_edge` is a **total pixel volume budget** (`num_frames × H × W`). When you feed more frames, `smart_resize` automatically shrinks spatial resolution to stay within budget. So you can trade resolution for fps — but only if `max_frames` allows enough frames through.

### The `max_frames` bottleneck

From vLLM's `_get_video_second_idx` (in `qwen3_vl.py`), which calls HF's `sample_frames`:

```python
num_frames = int(duration_seconds * fps)                        # e.g., 5400 * 0.5 = 2700
num_frames = min(max(num_frames, min_frames), max_frames)       # clamped to 768!
```

Per-request `num_frames` or `fps` are **also clamped** to `max_frames`. So `max_frames` **must be raised at startup** — it cannot be overridden per-request.

### How `smart_resize` trades resolution for frames

From HF's `smart_resize()` in `video_processing_qwen3_vl.py`:

```python
# factor = patch_size * merge_size = 16 * 2 = 32
# temporal_factor = temporal_patch_size = 2

h_bar = round(height / 32) * 32
w_bar = round(width / 32) * 32
t_bar = round(num_frames / 2) * 2

if t_bar * h_bar * w_bar > max_pixels:        # total volume exceeds budget
    beta = sqrt(num_frames * H * W / max_pixels)
    h_bar = max(32, floor(H / beta / 32) * 32)  # shrink both dims proportionally
    w_bar = max(32, floor(W / beta / 32) * 32)
```

Both dimensions are shrunk proportionally by `beta`, then floored to multiples of 32.

## The Two Knobs

| Knob | Set where | What it does |
|------|-----------|--------------|
| `max_frames` | **Startup only** via `--mm-processor-kwargs` | Hard cap on sampled frame count. Read from the default video processor instance by vLLM's `_get_video_second_idx`. Cannot be overridden per-request. |
| `fps` | Per-request via `mm_processor_kwargs` | Sampling rate. But frame count is still capped by `max_frames`. |
| `longest_edge` | Per-request via `mm_processor_kwargs` | Total pixel budget. `smart_resize` auto-reduces resolution when frames increase. |

## Startup Change

Add `"max_frames"` to the existing `--mm-processor-kwargs`:

```bash
--mm-processor-kwargs '{"size": {"longest_edge": 67108864, "shortest_edge": 4096}, "max_frames": 2700}'
```

This allows up to 2700 frames (0.5 fps on a 90-min video). The encoder cache stays at 32K tokens (unchanged, since it's derived from `longest_edge` with 2 frames, not `max_frames`).

**Safety**: Raising `max_frames` is safe for profiling/warmup — the warmup always uses 2 frames, and the encoder cache budget depends on `longest_edge` (not `max_frames`).

**Image leak risk**: The flat form might leak `max_frames` to the image processor. Since `--limit-mm-per-prompt '{"image": 0}'` disables images, this is harmless. If startup still errors, try the scoped form: `"videos_kwargs": {"max_frames": 2700}` (vLLM's profiling ignores scoped kwargs, but `max_frames` isn't used in profiling).

## Per-Request Experimentation Matrix

Once `max_frames=2700` is set at startup, control the tradeoff per-request via `mm_processor_kwargs` in API calls.

### 90-min (5400s) video at 0.5 fps = 2700 frames

| Per-request `longest_edge` | Resolution (W×H) | Tokens | Downscale | Fits 32K cache? |
|---------------------------|-------------------|--------|-----------|-----------------|
| 67M (32K budget) | 64×64 | ~5,400 | 108× | Yes |
| 134M (64K budget) | 128×96 | ~16,200 | 36× | Yes |
| 268M (128K budget) | 160×128 | ~27,000 | 17× | Yes |

All three stay within the 32K encoder cache budget.

### Example API request

```json
{
    "mm_processor_kwargs": {
        "size": {"longest_edge": 134217728},
        "fps": 0.5
    }
}
```

### Shorter videos (where 0.5 fps < 768 frames)

`max_frames` doesn't kick in for videos where `duration × fps < 768`:

| Duration | Frames at 0.5 fps | `max_frames` active? |
|----------|--------------------|---------------------|
| 5 min | 150 | No |
| 10 min | 300 | No |
| 30 min | 900 | Yes (clamped to 900, since 900 < 2700) |
| 60 min | 1800 | No |
| 90 min | 2700 | No (exactly at limit) |

## Upgrading to Higher FPS Later

If 0.5 fps proves insufficient after experimentation, restart with a higher `max_frames`:

| `max_frames` | Max fps on 90-min | Per-frame resolution impact |
|-------------|-------------------|-----------------------------|
| 2700 | 0.5 fps | Baseline |
| 5400 | 1.0 fps | ~2× lower per-frame resolution |
| 10800 | 2.0 fps | ~4× lower per-frame resolution |

The per-request `longest_edge` would need to decrease proportionally to stay within the 32K token budget. For example, at 5400 frames with `longest_edge=134M`, resolution drops to ~96×64.

## Source Code References

- **vLLM frame clamping**: `vllm/model_executor/models/qwen3_vl.py` → `Qwen3VLProcessingInfo._get_video_second_idx`
- **HF frame sampling**: `transformers/models/qwen3_vl/video_processing_qwen3_vl.py` → `Qwen3VLVideoProcessor.sample_frames`
- **HF spatial resize**: `transformers/models/qwen3_vl/video_processing_qwen3_vl.py` → `smart_resize()`
- **vLLM token calculation**: `vllm/model_executor/models/qwen3_vl.py` → `Qwen3VLProcessingInfo._get_vision_info`
