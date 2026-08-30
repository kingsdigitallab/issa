# Qwen3.8-27B Video Processing Analysis

How 768×576 videos are downsampled by vLLM's Qwen3VL video preprocessor, as a function of the `longest_edge` pixel budget and video duration.

## Pipeline overview (3 stages)

All logic below is grounded in the actual source code from:

- **HuggingFace**: `transformers/models/qwen3_vl/video_processing_qwen3_vl.py` (`Qwen3VLVideoProcessor`, `smart_resize`)
- **vLLM**: `vllm/model_executor/models/qwen3_vl.py` (`Qwen3VLProcessingInfo._get_video_second_idx`, `_get_vision_info`)

### Stage 1: Frame sampling (temporal)

With `--media-io-kwargs '{"video": {"num_frames": -1}}'`, vLLM loads **all** video frames. Then, with `do_sample_frames=True` and `fps=2` (the model card's recommended defaults):

```python
# vLLM's _get_video_second_idx calls HF's sample_frames:
num_frames = int(duration_seconds * fps)          # fps=2 → 2 frames per second
num_frames = min(max(num_frames, min_frames), max_frames)  # clamp to [4, 768]
indices = np.linspace(0, total_frames - 1, num_frames).round().astype(int)
```

**Critical**: `max_frames=768` means videos longer than **384 seconds (6.4 min)** are capped at 768 frames. The effective FPS drops below 2 for longer videos.

### Stage 2: Spatial resize (`smart_resize`)

`longest_edge` is a **total pixel volume budget** across all frames, not per-frame:

```python
# From HF's smart_resize():
# factor = patch_size * merge_size = 16 * 2 = 32
# temporal_factor = temporal_patch_size = 2

h_bar = round(height / 32) * 32    # round to multiple of 32
w_bar = round(width / 32) * 32
t_bar = round(num_frames / 2) * 2  # round to even

if t_bar * h_bar * w_bar > max_pixels:   # BUDGET EXCEEDED
    beta = sqrt(num_frames * H * W / max_pixels)
    h_bar = max(32, floor(H / beta / 32) * 32)   # shrink both dims proportionally
    w_bar = max(32, floor(W / beta / 32) * 32)
```

Both dimensions are shrunk proportionally by `beta`, then floored to multiples of 32.

### Stage 3: Token count

```
grid_t = padded_frames / 2          (temporal compression)
grid_h = resized_H / 16             (patch height)
grid_w = resized_W / 16             (patch width)
tokens = (grid_t × grid_h × grid_w) / 4   (merge_size² spatial merge)
```

## Fixed parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| `patch_size` | 16 | `video_preprocessor_config.json` |
| `temporal_patch_size` | 2 | `video_preprocessor_config.json` |
| `merge_size` | 2 | `video_preprocessor_config.json` |
| `factor` | 32 | `patch_size × merge_size` |
| `min_frames` | 4 | `processor_config.json` |
| `max_frames` | 768 | `processor_config.json` |
| `fps` | 2 | `processor_config.json` |
| `do_sample_frames` | True | `processor_config.json` |
| `shortest_edge` | 4,096 | `video_preprocessor_config.json` |

## Results for 768×576 videos

The `longest_edge` pixel values corresponding to each token budget tier:

- **12K** tokens = `longest_edge = 25,165,824` (model default)
- **32K** tokens = `longest_edge = 67,108,864`
- **64K** tokens = `longest_edge = 134,217,728`
- **128K** tokens = `longest_edge = 268,435,456`

| Budget | Duration | Frames | Eff. FPS | Resolution (W×H) | Grid T×H×W | Tokens | Downscale |
|--------|----------|--------|----------|-------------------|------------|--------|-----------|
| **12K** | 5 min | 600 | 2.0 | 224×160 | 300×10×14 | 10,500 | 12.3× |
| **12K** | 10 min | 768 | 1.3 | 192×128 | 384×8×12 | 9,216 | 18.0× |
| **12K** | 30 min | 768 | 0.4 | 192×128 | 384×8×12 | 9,216 | 18.0× |
| **12K** | 60 min | 768 | 0.2 | 192×128 | 384×8×12 | 9,216 | 18.0× |
| **12K** | 90 min | 768 | 0.1 | 192×128 | 384×8×12 | 9,216 | 18.0× |
| **32K** | 5 min | 600 | 2.0 | 384×288 | 300×18×24 | 32,400 | 4.0× |
| **32K** | 10 min | 768 | 1.3 | 320×256 | 384×16×20 | 30,720 | 5.4× |
| **32K** | 30 min | 768 | 0.4 | 320×256 | 384×16×20 | 30,720 | 5.4× |
| **32K** | 60 min | 768 | 0.2 | 320×256 | 384×16×20 | 30,720 | 5.4× |
| **32K** | 90 min | 768 | 0.1 | 320×256 | 384×16×20 | 30,720 | 5.4× |
| **64K** | 5 min | 600 | 2.0 | 544×384 | 300×24×34 | 61,200 | 2.1× |
| **64K** | 10 min | 768 | 1.3 | 480×352 | 384×22×30 | 63,360 | 2.6× |
| **64K** | 30 min | 768 | 0.4 | 480×352 | 384×22×30 | 63,360 | 2.6× |
| **64K** | 60 min | 768 | 0.2 | 480×352 | 384×22×30 | 63,360 | 2.6× |
| **64K** | 90 min | 768 | 0.1 | 480×352 | 384×22×30 | 63,360 | 2.6× |
| **128K** | 5 min | 600 | 2.0 | 768×576 | 300×36×48 | 129,600 | 1.0× (native!) |
| **128K** | 10 min | 768 | 1.3 | 672×512 | 384×32×42 | 129,024 | 1.3× |
| **128K** | 30 min | 768 | 0.4 | 672×512 | 384×32×42 | 129,024 | 1.3× |
| **128K** | 60 min | 768 | 0.2 | 672×512 | 384×32×42 | 129,024 | 1.3× |
| **128K** | 90 min | 768 | 0.1 | 672×512 | 384×32×42 | 129,024 | 1.3× |

## Key takeaways

1. **`max_frames=768` is the first bottleneck** — for any video ≥ 6.4 min, the frame count is capped at 768 regardless of budget. A 90-min video gets the same 768 frames as a 10-min video, but spread over 90 min → 0.1 effective FPS (one frame every ~7 seconds).

2. **`longest_edge` trades spatial resolution for frame count** — when the pixel budget is too small, `smart_resize` shrinks both dimensions proportionally. At 12K tokens, a 10-min video is downscaled to 192×128 (18× reduction from 768×576).

3. **128K is the sweet spot for 768×576** — at 128K, a 5-min video gets **native resolution** (768×576, no downscale), and longer videos only need 1.3× downscale (672×512).

4. **The `cap_pixels_per_frame` option** (currently disabled, emits a warning) would change behavior: instead of treating `longest_edge` as a total budget, it caps per-frame pixels at `max_video_tokens=768` patches/frame. This prevents short videos from spending the entire budget on a few high-resolution frames. The HF code warns this will become the default in transformers v5.22.

5. **You can increase `max_frames`** via `mm_processor_kwargs` (e.g., `"max_frames": 2048`) to get more temporal detail for long videos, at the cost of more tokens. You can also increase `fps` (e.g., `fps=4`) for denser temporal sampling, also at higher token cost.
