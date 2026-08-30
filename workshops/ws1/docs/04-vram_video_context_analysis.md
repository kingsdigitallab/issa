# VRAM Video Context Analysis: Maximising FPS and Resolution for Programme Boundary Detection

## Summary

This analysis determines the maximum video context the A100 80GB can afford when running Qwen3.8-27B-INT4 on vLLM 0.28.0, to achieve **minimum 1 fps** (ideally 1.5) on 30-90 minute videos with **50-70% spatial resolution reduction**. The key finding: by enabling FP8 KV cache, YaRN context extension (factor=2.0, 512K max-model-len), and raising the encoder budget to 224K tokens, the GPU can support 1.5 fps on 90-min videos at 256x192 (67% reduction) or 1 fps at 320x224 (59% reduction) — both within the target range.

## Current Setup

### vllm.sh (startup)

| Flag | Current value | Effect |
|------|---------------|--------|
| `--max-model-len` | 256k (262,144) | Total context: video + prompt + reasoning + output |
| `--gpu-memory-utilization` | 0.70 | vLLM gets ~55.5 GiB; ~23.8 GiB headroom for encoder |
| `--mm-processor-kwargs` | `longest_edge=268M, shortest_edge=4096` | Encoder cache budget = 128K video tokens |
| `--kv-cache-dtype` | (bf16, default) | 64 KB/token for 16 attention layers |
| `--skip-mm-profiling` | yes | Skips dummy encoder forward at startup (avoids OOM) |
| `--media-io-kwargs` | `{"video": {"num_frames": -1}}` | Loads all frames from disk, then samples |
| `max_frames` | 768 (processor default) | **Bottleneck**: caps frame count for any video >= 6.4 min |
| `fps` | 2 (processor default) | Sampling rate, but clamped by max_frames |

### answer_videos_vlm.bash (per-request)

| Env var | Value | Effect |
|---------|-------|--------|
| `ANSWER_VIDEOS_VLM_VIDEO_TOKENS` | 64k | Per-request `longest_edge` = 64K x 2048 = 134M |
| `ANSWER_VIDEOS_VLM_MAX_TOKENS` | 30k | Max output tokens |
| `ANSWER_VIDEOS_VLM_REASONING_EFFORT` | xhigh | Deep reasoning (~30-50K tokens per request) |

## Three Independent Bottlenecks

### 1. `max_frames=768` caps FPS

From vLLM's `_get_video_second_idx` (`qwen3_vl.py:1060-1080`):

```python
num_frames = int(total_num_frames / metadata["fps"] * sampled_fps)
num_frames = min(max(num_frames, min_frames), video_processor.max_frames)  # clamped to 768!
```

A 90-min video at default fps=2 produces 10,800 frames, but only 768 are kept → effective **0.14 fps** (one frame every ~7 seconds). This is far too sparse for detecting programme boundaries that appear for barely a second.

`max_frames` is read from the processor's default config (set at startup via `--mm-processor-kwargs`). It **cannot be overridden per-request** — the per-request `fps` or `num_frames` are also clamped to it.

### 2. `max-model-len=256K` limits total context

With ~82K overhead (50K reasoning + 30K output + 2K prompt), only **~174K tokens** remain for video. At 1 fps on a 90-min video (5400 frames), 320x224 resolution produces ~185K video tokens — exceeding 174K.

The model's `max_position_embeddings=262,144` (256K) caps `--max-model-len` at 256K. Extending beyond requires **YaRN RoPE scaling**, which Qwen officially supports (see below).

### 3. Encoder budget (128K) limits video tokens

The startup `longest_edge` determines the encoder cache slot budget:

```
encoder_budget_tokens = longest_edge / 2048
```

At `longest_edge=268M` (current): budget = 128K tokens. At `longest_edge=469M` (Qwen recommended): budget = 224K tokens.

The per-request `longest_edge` (from `ANSWER_VIDEOS_VLM_VIDEO_TOKENS`) can be lower than the startup value but should not exceed it (risks encoder cache exhaustion).

## Model Architecture (from config.json)

Fetched from `https://huggingface.co/RedHatAI/Qwen3.8-27B-INT4/raw/main/config.json`:

### LLM (text_config)

| Parameter | Value |
|-----------|-------|
| `hidden_size` | 5120 |
| `num_hidden_layers` | 64 |
| `layer_types` | 48 linear_attention + 16 full_attention (every 4th layer) |
| `num_attention_heads` | 24 (full attention layers) |
| `num_key_value_heads` | 4 |
| `head_dim` | 256 |
| `max_position_embeddings` | 262,144 (256K) |
| `rope_type` | default (mrope, interleaved) |
| `rope_theta` | 10,000,000 |
| `mrope_section` | [11, 11, 10] (temporal, height, width) |

### Vision (vision_config)

| Parameter | Value |
|-----------|-------|
| `hidden_size` | 1152 (ViT internal) |
| `out_hidden_size` | 5120 (= LLM hidden_size) |
| `depth` | 27 (ViT layers) |
| `patch_size` | 16 |
| `spatial_merge_size` | 2 |
| `temporal_patch_size` | 2 |
| `deepstack_visual_indexes` | [] (empty — no deepstack overhead) |
| `in_channels` | 3 |

## Memory Costs

### KV cache (16 full_attention layers only)

GDN (48 linear_attention layers) use a fixed recurrent state (~0.02 GiB), not per-token KV.

| dtype | Per-token cost | Formula |
|-------|---------------|---------|
| bf16 | 65,536 bytes (64 KB) | 2 (K+V) x 4 (KV heads) x 256 (head_dim) x 2 (bytes) x 16 (layers) |
| fp8 | 32,768 bytes (32 KB) | Same but 1 byte per element |

### Encoder cache (GPU, dynamic)

Per-token cost: `out_hidden_size x sizeof(dtype) = 5120 x 2 = 10,240 bytes (10 KB)`

No deepstack overhead (`deepstack_visual_indexes=[]`). The encoder cache is NOT pre-allocated; it grows dynamically as videos are encoded and shrinks on eviction.

### Encoder activation (during ViT forward pass)

The ViT processes **all frames in one batched forward pass** (`qwen3_vl.py:2261-2284`). The attention is per-frame (via `cu_seqlens`), but all patch embeddings are stored simultaneously.

**Critical insight**: `total_patches = token_budget x 4`, regardless of how frames are distributed (many small frames vs few large frames). The encoder activation is bounded by `longest_edge`, NOT by `max_frames`.

Estimated peak per patch: ~11,520 bytes (hidden states + peak MLP intermediate in bf16).

| Encoder budget | Total patches | Activation | Cache | Total | + 1.5x safety |
|----------------|--------------|------------|-------|-------|---------------|
| 128K (longest_edge=268M) | 524,288 | 5.7 GiB | 1.25 GiB | 6.9 GiB | 10.4 GiB |
| 192K (longest_edge=393M) | 786,432 | 8.5 GiB | 1.88 GiB | 10.4 GiB | 15.6 GiB |
| 224K (longest_edge=469M) | 917,504 | 9.9 GiB | 2.19 GiB | 12.1 GiB | 18.2 GiB |
| 256K (longest_edge=524M) | 1,048,576 | 11.3 GiB | 2.50 GiB | 13.8 GiB | 20.7 GiB |

### Previous OOM at 224K

The previous OOM with `longest_edge=469M` (224K) occurred **during startup profiling** (before `--skip-mm-profiling` was added). The dummy encoder forward created a float32 pixel tensor of ~5.6 GiB, plus ViT activations. The `SIGKILL` was likely from the **Linux kernel OOM killer (system RAM)**, not a CUDA OOM (GPU VRAM). With `--skip-mm-profiling` (already in use), the dummy forward is skipped entirely.

At runtime, the real video encoding uses bf16 (not float32), and the analysis shows ~12 GiB for 224K tokens, well within the 23.8 GiB headroom at 0.70 utilization.

## GPU Memory Budget

```
GPU: A100 80GB (~79.25 GiB usable)

Fixed costs (from startup logs):
  Model weights (INT4):     18.24 GiB
  Non-torch overhead:        ~0.24 GiB  (included in 18.24)
  CUDAGraph:                  1.04 GiB
  LM peak activation:        2.11 GiB
  ─────────────────────────────────────
  Total fixed:              ~21.39 GiB

At gpu_memory_utilization=0.70:
  vLLM allocation:    0.70 x 79.25 = 55.48 GiB
  KV cache:           55.48 - 21.39 = 34.09 GiB
  Headroom:          79.25 - 55.48 = 23.78 GiB  (for encoder at runtime)

FP8 KV cache at 512K max-model-len:
  Needed:     524,288 x 32KB = 15.63 GiB
  Available:  34.09 GiB
  Spare:      18.46 GiB  (plenty)

bf16 KV cache at 512K max-model-len (for comparison):
  Needed:     524,288 x 64KB = 31.25 GiB
  Available:  34.09 GiB
  Spare:       2.84 GiB  (barely fits)

Encoder at 224K tokens:
  Total:      ~12.1 GiB  < 23.78 GiB headroom  (comfortable)
  With 1.5x safety: ~18.2 GiB < 23.78 GiB  (still fits)
```

### Utilization tradeoff

| `gpu_memory_utilization` | KV cache available | Headroom | 224K encoder fits? |
|--------------------------|-------------------|----------|---------------------|
| 0.65 | 30.12 GiB | 27.74 GiB | Yes (very comfortable) |
| 0.70 | 34.09 GiB | 23.78 GiB | Yes (comfortable) |
| 0.75 | 38.05 GiB | 19.81 GiB | Yes (with 1.5x safety: tight) |
| 0.80 | 42.01 GiB | 15.85 GiB | Yes (by estimate), No (with 1.5x safety) |
| 0.85 | 45.97 GiB | 11.89 GiB | Marginal even without safety factor |

**Recommendation**: Start at 0.70 (current). If more KV cache is needed (e.g., longer reasoning), try 0.75. Do not exceed 0.80 with 224K encoder budget.

## YaRN Context Extension

### Official Qwen support

From the Qwen3.8-27B model card (`https://huggingface.co/Qwen/Qwen3.8-27B`):

> Context Length: 262,144 natively and extensible up to 1,000,000 tokens.
>
> For long-horizon tasks where the total length exceeds this limit, we recommend using RoPE scaling techniques, e.g., YaRN.
>
> if the typical context length for your application is 524,288 tokens, it would be better to set factor as 2.0.

The model card provides the exact vLLM command:

```bash
VLLM_ALLOW_LONG_MAX_MODEL_LEN=1 vllm serve ... \
  --hf-overrides '{"text_config": {"rope_parameters": {"mrope_interleaved": true, "mrope_section": [11, 11, 10], "rope_type": "yarn", "rope_theta": 10000000, "partial_rotary_factor": 0.25, "factor": 2.0, "original_max_position_embeddings": 262144}}}' \
  --max-model-len 524288
```

### How it works in vLLM 0.28.0

`--hf-overrides` accepts a JSON dict (`arg_utils.py:548`, `model.py:488-503`). Nested configs (like `text_config`) are recursively updated via `_update_nested`. The rope parameters are passed to `get_rope()` (`rotary_embedding/__init__.py:243-272`), which creates an `MRotaryEmbedding` with `scaling_factor` when `mrope_section` is present and `rope_type == "yarn"`.

The `derived_max_model_len` calculation (`model.py:2381-2413`) multiplies `original_max_position_embeddings` by `factor`, so `--max-model-len 524288` is allowed without `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` (since 524288 == 262144 x 2.0). Set the env var as a safety net.

### Quality note

From the model card:

> All the notable open-source frameworks implement static YaRN, which means the scaling factor remains constant regardless of input length, potentially impacting performance on shorter texts. We advise modifying the rope_parameters configuration only when processing long contexts is required.

Since this use case involves long videos (30-90 min), YaRN is appropriate. For shorter texts, the impact should be negligible with factor=2.0 (a modest extension).

## Token Calculation

### Formula

```
tokens = (grid_t x grid_h x grid_w) / merge_size^2

Where:
  grid_t = padded_frames / temporal_patch_size    (= N / 2, N rounded up to even)
  grid_h = resized_height / patch_size             (= H / 16)
  grid_w = resized_width / patch_size              (= W / 16)
  merge_size = 2

Simplified: tokens = N x H x W / 2048
```

### Budget to longest_edge mapping

```
longest_edge = video_tokens x 2048
```

Where `2048 = temporal_patch_size x patch_size^2 x merge_size^2 = 2 x 16^2 x 2^2`.

| Token budget | longest_edge | Note |
|--------------|-------------|------|
| 64K | 134,217,728 | Current per-request |
| 128K | 268,435,456 | Current startup |
| 192K | 393,216,000 | Mid-range option |
| **224K** | **469,762,048** | **Qwen recommended for hour-scale videos** |
| 256K | 524,288,000 | Aggressive |

### smart_resize behavior

HF's `video_smart_resize` (from `transformers.models.qwen3_vl.video_processing_qwen3_vl`) shrinks both dimensions proportionally when `total_pixels > longest_edge`:

```python
beta = sqrt(num_frames * H * W / longest_edge)
h_bar = max(32, floor(H / beta / 32) * 32)  # multiples of 32
w_bar = max(32, floor(W / beta / 32) * 32)
```

For 768x576 input (4:3 aspect ratio), the output maintains approximately 4:3 ratio, floored to multiples of 32.

## Expected Results

### With 224K encoder budget, default fps=2, max_frames=8100

The fps stays at the processor default (2.0). `max_frames=8100` only kicks in for long videos. Shorter videos get native or near-native resolution.

| Duration | Frames at fps=2 | Clamped? | Effective fps | Resolution | Video tokens | Total (82K overhead) |
|----------|----------------|----------|---------------|------------|-------------|----------------------|
| 5 min | 600 | No | 2.0 | 768x576 (native!) | ~150K | 232K |
| 10 min | 1,200 | No | 2.0 | 768x576 (native!) | ~150K | 232K |
| 30 min | 3,600 | No | 2.0 | 576x416 | ~150K | 232K |
| 60 min | 7,200 | No | 2.0 | 320x224 | ~185K | 267K |
| 90 min | 10,800 | Yes (8100) | 1.5 | 256x192 | ~190K | 272K |

All fit within 512K max-model-len. The 90-min case achieves 1.5 fps (above the 1 fps minimum).

### With per-request fps=1.0 (if framesense adds support)

| Duration | Frames at fps=1 | Clamped? | Effective fps | Resolution | Video tokens | Total (82K overhead) |
|----------|----------------|----------|---------------|------------|-------------|----------------------|
| 30 min | 1,800 | No | 1.0 | 576x416 | ~150K | 232K |
| 60 min | 3,600 | No | 1.0 | 384x288 | ~150K | 232K |
| 90 min | 5,400 | No | 1.0 | 320x224 | ~185K | 267K |

At 1 fps, 90-min videos get 320x224 (59% reduction in each dimension), which is in the middle of the 50-70% target range.

### With per-request fps=1.5

| Duration | Frames at fps=1.5 | Clamped? | Effective fps | Resolution | Video tokens | Total (82K overhead) |
|----------|-------------------|----------|---------------|------------|-------------|----------------------|
| 60 min | 5,400 | No | 1.5 | 320x224 | ~185K | 267K |
| 90 min | 8,100 | No | 1.5 | 256x192 | ~190K | 272K |

At 1.5 fps, 90-min videos get 256x192 (67% reduction), at the upper end of the target range.

## Proposed Configuration

### vllm.sh changes

```bash
MODEL_NAME="RedHatAI/Qwen3.8-27B-INT4"
CONTEXT="524288"
COLLECTION_PATH=/scratch/prj/dh_issa/issa/workshops/ws1/sample11
SING_FILE="/scratch/prj/dh_issa/sglang/vllm-openai_v0.28.0-cu130.sif"

SINGULARITYENV_VLLM_LOGGING_LEVEL=DEBUG \
SINGULARITYENV_VLLM_ALLOW_LONG_MAX_MODEL_LEN=1 \
singularity exec --nv \
    --bind $COLLECTION_PATH:$COLLECTION_PATH \
    --bind $HF_HOME:$HF_HOME \
    $SING_FILE \
    vllm serve $MODEL_NAME \
        --enable-log-requests \
        --log-error-stack \
        --uvicorn-log-level debug \
        --reasoning-parser qwen3 \
        --port 30000 \
        --tensor-parallel-size 1 \
        --max-model-len $CONTEXT \
        --hf-overrides '{"text_config": {"rope_parameters": {"mrope_interleaved": true, "mrope_section": [11, 11, 10], "rope_type": "yarn", "rope_theta": 10000000, "partial_rotary_factor": 0.25, "factor": 2.0, "original_max_position_embeddings": 262144}}}' \
        --allowed-local-media-path "/scratch/prj/dh_issa/issa/workshops/ws1/sample11" \
        --enable-chunked-prefill --max-num-batched-tokens 8192 \
        --kv-cache-dtype fp8 \
        --mm-processor-kwargs '{"size": {"longest_edge": 469762048, "shortest_edge": 4096}, "max_frames": 8100}' \
        --limit-mm-per-prompt '{"image": 0, "video": 1}' \
        --skip-mm-profiling \
        --mm-processor-cache-gb 0 \
        --gpu-memory-utilization 0.70 \
        --media-io-kwargs '{"video": {"num_frames": -1}}'
```

### Summary of changes vs current

| Flag | Current | Proposed | Why |
|------|---------|----------|-----|
| `--max-model-len` | 256k | 524288 (512K) | Fits 190K video + 82K overhead with margin |
| `--hf-overrides` | (none) | YaRN factor=2.0 | Officially supported by Qwen; extends context to 512K |
| `--kv-cache-dtype` | (bf16) | fp8 | Halves KV cache per token (32KB), frees VRAM |
| `--mm-processor-kwargs` | `longest_edge=268M` | `longest_edge=469M, max_frames=8100` | 224K encoder budget (Qwen recommended) + allows 1.5 fps on 90 min |
| `SINGULARITYENV_VLLM_ALLOW_LONG_MAX_MODEL_LEN` | (not set) | 1 | Safety net for YaRN override |
| `fps` | (not set, defaults to 2) | **Not set** (remains dynamic) | Qwen processor decides fps; max_frames caps long videos |
| `--gpu-memory-utilization` | 0.70 | 0.70 (unchanged) | 23.8 GiB headroom sufficient for 224K encoder |

### Notes on fps control

- **Default behavior**: fps=2 (processor default) with max_frames=8100. Shorter videos get 2 fps; 90-min videos are clamped to 1.5 fps. Resolution auto-adjusts via `smart_resize`.
- **Per-request override**: If framesense.py passes `fps` via `mm_processor_kwargs` in the API request, it overrides the default. Example:
  ```json
  {"mm_processor_kwargs": {"fps": 1.0}}
  ```
  This would give 90-min videos 1 fps at 320x224 (better resolution, lower temporal density). The startup `max_frames=8100` still acts as the cap.
- **Implementation**: framesense.py would need to pass `fps` in the `extra_body.mm_processor_kwargs` field of the OpenAI API call. If no fps is specified (or fps <= 0), the Qwen processor default (fps=2) applies.

### answer_videos_vlm.bash changes

```bash
ANSWER_VIDEOS_VLM_VIDEO_TOKENS="224k"   # was "64k" — match new encoder budget
ANSWER_VIDEOS_VLM_MAX_TOKENS="30k"      # unchanged
ANSWER_VIDEOS_VLM_REASONING_EFFORT="xhigh"  # unchanged
```

### What does NOT change

- `--skip-mm-profiling` — still needed (dummy encoder forward at 224K would stress system RAM)
- `--mm-processor-cache-gb 0` — still disabling CPU processor cache
- `--media-io-kwargs '{"video": {"num_frames": -1}}'` — still loading all frames
- `--limit-mm-per-prompt '{"image": 0, "video": 1}'` — still one video per request
- `--enable-chunked-prefill --max-num-batched-tokens 8192` — still chunked prefill

## Testing Methodology

### Step 1: Deploy and verify startup

1. Update `vllm.sh` with the proposed changes
2. Start the server
3. Check logs for:
   - `Using max model len 524288` (YaRN applied)
   - `KV cache: X GiB (Y blocks x Z tokens/block)` — should show ~34 GiB (fp8, more blocks than bf16)
   - No errors from `--hf-overrides` or YaRN initialization
4. If startup fails with YaRN, check that `SINGULARITYENV_VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` is set

### Step 2: Test with a short video (5-10 min)

1. Send a request with `ANSWER_VIDEOS_VLM_VIDEO_TOKENS=224k`
2. Verify the pipeline works end-to-end
3. Check vLLM debug logs for `grid_thw` — should show native resolution (768x576)
4. Monitor `nvidia-smi` during processing — encoder peak should be < 12 GiB above baseline

### Step 3: Test with a 90-min video (default fps=2)

1. Send the request
2. Check `grid_thw` in logs — should show ~256x192 (8100 frames clamped from 10,800)
3. Monitor GPU memory — peak should stay under ~68 GiB (55.5 baseline + 12 encoder)
4. Evaluate detection quality vs previous results

### Step 4: Push limits (optional)

If Step 3 succeeds and you want more:

| What to try | How | Expected effect |
|-------------|-----|-----------------|
| 1 fps (better resolution) | Pass `mm_processor_kwargs: {"fps": 1.0}` per-request | 320x224 for 90 min |
| Higher utilization | `--gpu-memory-utilization 0.75` | More KV cache, less headroom (19.8 GiB) |
| Larger encoder budget | `longest_edge=524M` (256K tokens) | Better resolution, but encoder needs ~13.8 GiB |
| Even longer context | YaRN factor=4.0, `--max-model-len 1000000` | Allows 400K+ video tokens for longer reasoning |

If OOM occurs:
- Lower `gpu-memory-utilization` to 0.65 (more headroom for encoder)
- Or reduce `longest_edge` (smaller encoder budget = less activation memory)
- Or reduce `max_frames` (fewer frames = same total tokens but different distribution)

### Monitoring commands

```bash
# Watch GPU memory during video processing
watch -n 1 nvidia-smi

# Check vLLM KV cache allocation in logs
grep "KV cache" /path/to/vllm.log

# Check grid_thw (resolution) in debug logs
grep "grid_thw" /path/to/vllm.log

# Check encoder cache budget
grep "Encoder cache" /path/to/vllm.log
```

## Alternative: No YaRN (Conservative)

If YaRN quality impact is a concern, a configuration without YaRN can still achieve 1 fps on 90-min videos, but at lower resolution:

| Encoder budget | longest_edge | 90-min @ 1 fps resolution | Tokens | Fits 256K? |
|----------------|-------------|--------------------------|--------|------------|
| 128K (current) | 268M | 256x192 (67% reduction) | 127K | Yes (127K + 82K = 209K) |
| 192K | 393M | 288x224 (63% reduction) | 166K | Yes (166K + 82K = 248K, tight) |
| 224K | 469M | 320x224 (59% reduction) | 185K | **No** (185K + 82K = 267K > 256K) |

Without YaRN, 128K encoder budget gives 256x192 at 1 fps (fits in 256K). 192K gives 288x224 (tight fit). 224K does NOT fit without YaRN.

## Source References

- **Model config**: `https://huggingface.co/RedHatAI/Qwen3.8-27B-INT4/raw/main/config.json`
- **Qwen model card (YaRN instructions)**: `https://huggingface.co/Qwen/Qwen3.8-27B`
- **vLLM `--hf-overrides`**: `vllm/engine/arg_utils.py:548`, `vllm/config/model.py:488-503`
- **vLLM YaRN + mrope**: `vllm/model_executor/layers/rotary_embedding/__init__.py:243-272`
- **vLLM max_model_len verification**: `vllm/config/model.py:2381-2465`
- **vLLM encoder cache sizing**: `vllm/multimodal/encoder_budget.py:45-130`, `vllm/v1/core/encoder_cache_manager.py:282-329`
- **vLLM encoder cache (GPU)**: `vllm/v1/worker/gpu_model_runner.py:621` (dict, not pre-allocated)
- **vLLM ViT forward (all frames at once)**: `vllm/model_executor/models/qwen3_vl.py:2261-2284`
- **vLLM frame sampling**: `vllm/model_executor/models/qwen3_vl.py:1060-1080` (`_get_video_second_idx`)
- **vLLM video token calculation**: `vllm/model_executor/models/qwen3_vl.py:966-973` (`_get_vision_info`)
- **vLLM max_video_tokens (budget)**: `vllm/model_executor/models/qwen3_vl.py:991-1017` (`get_max_video_tokens`)
- **vLLM memory budget split**: `vllm/v1/worker/gpu_worker.py:513-626`
- **vLLM `--skip-mm-profiling`**: `vllm/config/multimodal.py:217-223`, `vllm/v1/worker/gpu_model_runner.py:6558-6631`
- **vLLM per-request mm_processor_kwargs merge**: `vllm/renderers/params.py:43-68` (`recursively_merge_kwargs`)
- **HF smart_resize**: `transformers/models/qwen3_vl/video_processing_qwen3_vl.py` (`video_smart_resize`)
