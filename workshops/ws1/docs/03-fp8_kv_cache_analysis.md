# FP8 KV Cache Analysis for Qwen3.8-27B on A100 80GB

## Summary

Enabling FP8 KV cache (`--kv-cache-dtype fp8`) on Qwen3.8-27B roughly **doubles** the available KV cache capacity — from ~861K to ~1,681K tokens of context — with minimal impact on detection quality.

## Architecture Context

Qwen3.8-27B is a **hybrid model** with two types of recurrent layers:

| Component | Layers | Cache type | FP8-eligible? |
|-----------|--------|------------|---------------|
| Gated DeltaNet (GDN) | 48 | Recurrent state (SSM) | No — `--mamba-cache-dtype` only accepts bf16/fp16/fp32 |
| Gated Attention | 16 | Standard KV cache (K+V) | Yes — via `--kv-cache-dtype fp8` |

The GDN layers use a recurrent state instead of KV pairs, so their memory footprint per token is negligible compared to attention layers. The KV cache is **almost entirely** attention KV.

## Memory Breakdown

From your startup logs:

```
Free memory on device: 78.83/79.25 GiB
Consumed memory (weights + non-torch): 18.24 GiB
Peak activation: 2.11 GiB
CUDAGraph memory: 1.04 GiB
KV cache: 52.56 GiB (1098 blocks × 784 tokens/block)
```

### Per-token costs

**Attention KV (16 layers):**
- K+V per layer (bf16): `2 × 4 KV heads × 256 head_dim × 2 bytes` = 4,096 bytes
- K+V per layer (fp8): `2 × 4 KV heads × 256 head_dim × 1 byte` = 2,048 bytes
- Total per token (bf16): 4,096 × 16 = 65,536 bytes (64 KB)
- Total per token (fp8): 2,048 × 16 = 32,768 bytes (32 KB)

**GDN state (48 layers):**
- ~0.02 GiB total (negligible)

### Aggregate

| Component | bf16 (current) | FP8 | Savings |
|-----------|----------------|-----|---------|
| Attention KV cache (16 layers) | 52.54 GiB | 26.27 GiB | 26.27 GiB |
| GDN state (48 layers) | ~0.02 GiB | ~0.02 GiB (stays bf16) | 0 |
| **Total** | **52.56 GiB** | **26.29 GiB** | **~26 GiB** |

## Context Capacity Impact

Since vLLM fills all available GPU memory with KV cache, the freed ~26 GiB is repurposed for ~2× more blocks:

| Metric | bf16 (current) | FP8 |
|--------|----------------|-----|
| Blocks | 1,098 | ~2,195 |
| Block size | 784 tokens | 784 tokens |
| Context capacity | ~861K tokens | ~1,681K tokens |
| **Multiplier** | | **~2.0×** |

## How to Enable

Add to your `vllm serve` command:

```bash
--kv-cache-dtype fp8
```

`fp8` is an alias for `fp8_e4m3` (4-bit mantissa, 3-bit exponent). The A100 (Ampere, SM 8.0) supports this.

## Effect on Detection Quality

**Minimal for programme boundary detection**, for three reasons:

### 1. Dominant quality loss is spatial downscaling

At 32K token budget, your 768×576 video is already downscaled 5.4× to 320×256. FP8 quantization noise in the attention KV cache is far smaller than the information loss from that spatial downscaling.

### 2. FP8 with scale=1.0 on A100

Without Flash Attention 3 (Hopper-only) and llm-compressor calibration, you get per-tensor quantization with all scales = 1.0. This means bf16 values are simply cast to fp8_e4m3 (range [-448, 448], ~3.5 significant digits). Attention K/V values are typically within this range, so clipping is rare.

### 3. Reasoning is unaffected

The model weights (already INT4) and the LM forward pass remain in their native precision. Only the cached K/V tensors for the 16 attention layers are quantized.

## Practical Benefits for Your Setup

The 2× KV cache capacity doesn't directly increase your video token budget (that's limited by the encoder cache at 32K). But it helps in two ways:

1. **Higher `max-model-len`**: With 2× KV capacity, you could push `--max-model-len` toward 512K or beyond (with YaRN scaling), giving more room for long video tokens + reasoning + output.

2. **Freed GPU memory for encoder cache**: If you reduce `--gpu-memory-utilization` to leave headroom, the freed 26 GiB could allow a larger `longest_edge` at startup without OOM during warmup — potentially going from 32K to 64K or 128K encoder cache budget.

## Risk Mitigation

If you notice degraded detection of subtle visual separators:

- Try `fp8_e5m2` instead (5-bit exponent, 2-bit mantissa) — more dynamic range, less precision:
  ```bash
  --kv-cache-dtype fp8_e5m2
  ```

- Or calibrate scales with [llm-compressor](https://github.com/vllm-project/llm-compressor) before serving for optimal accuracy.

## Caveat: GDN State Cannot Be FP8

The `--mamba-cache-dtype` flag (which controls the GDN recurrent state) only accepts `auto`/`bfloat16`/`float16`/`float32` — no FP8 option. But as shown above, the GDN state is ~0.02 GiB, so this limitation is irrelevant for memory savings.

## Alternative: `--kv-cache-dtype-skip-layers`

For hybrid models, you can selectively skip FP8 quantization for specific attention layer types:

```bash
--kv-cache-dtype fp8 --kv-cache-dtype-skip-layers sliding_window
```

This lets you keep sensitive layers at bf16 while quantizing the rest. However, Qwen3.8's attention layers are standard (not sliding window), so this is unlikely to be needed.

## Source References

- **vLLM engine args**: `--kv-cache-dtype` in CacheConfig (`vllm/config/cache.py`)
- **vLLM quantized KV cache docs**: https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache/
- **vLLM quantization overview**: https://docs.vllm.ai/en/latest/features/quantization/
- **llm-compressor** (for calibration): https://github.com/vllm-project/llm-compressor
