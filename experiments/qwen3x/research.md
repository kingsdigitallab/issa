
## TODO

. debug -%
. add initial separator
. ask models to express timecodes in secs? They tend to do that anyway and avoid misinterpretaion of HH:MM:SS format
. add another video annotation
  . 2 from NI  - Done
  . 2 from NLS -
. only retain most diverse samples
DONE sep covers last 5 secs before prog => 100%
DONE debug prog match for DVC: (sep is rejected as it goes over tolerance zone)

### model selection: 

- qwen3.5 2b
- 4b
- 9b
- 3.5-27b
- 3.5-35b-a3b
- 3.6-27b
- 3.6-35b-a3b
- Qwen/Qwen3-VL-32B-Instruct 
    - needs >> 32k context, which doesn't fit into VRAM
    - tried -FP* with --chunked-prefill-size 2048 but v. slow, never responds...
    - TODO: python -m sglang.launch_server --model-path Qwen/Qwen3-VL-32B-Instruct --port 8000 --tp-size 1 --mem-fraction-static 0.8 --context-length 49152 --enable-deterministic-inference --kv-cache-dtype fp8_e4m3
    --enable-multimodal
- https://huggingface.co/OpenGVLab/InternVL3-8B (3.5 down't look better on videos according to their own benchmarks)
    - TODO: --enable-multimodal
    - results are poor, also on 3-14B
- https://huggingface.co/OpenMOSS-Team/MOSS-VL-Instruct-0408

### kv cache quantised to 8bits (kv_cache_dtype="fp8", or calibrate it) 

### speed up processing:

- qwen3.x-35b-a3b (-fp8)
- note that fp8 needs a ada, hopper or blackwell card
- --speculative-algorithm EAGLE --speculative-num-steps 3 -speculative-eagle-topk 1 --speculative-num-draft-tokens 4 # https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.6 (MTP)
    - OOM on 80g!
- w/ and without reasoning

### reduce amount of reasoning (to keep response within VRAM & reasonable processing time):
    - lower temp???
    - prompt (or system prompt)? Doesn't seem to make any difference with Q3.5

### reduce VRAM:
    - 4bits quants of model
        + python -m sglang.launch_server --model-path Qwen3.6-27B-Q4_K_M.gguf --tokenizer-path unsloth/Qwen3.6-27B-GGUF --served-model-name unsloth/Qwen3.6-27B-GGUF --port 8000 --tp-size 1 --mem-fraction-static 0.8 --context-length 49152 --enable-deterministic-inference --reasoning-parser qwen3  --mm-attention-backend fa3 --attention-backend fa3 --keep-mm-feature-on-device  --kv-cache-dtype fp8_e4m3
        + Q3.5 Arch GGUF NOT SUPPORTED YET by sglang...
    - 8bits quants of kv cache. --kv-cache-dtype fp8_e4m3 for low accuracy degradation

### other params:
    - --enable-multimodal # for qwen3-vl? on sglang
    - --mm-attention-backend fa3 --attention-backend fa3 --keep-mm-feature-on-device 
        + that is better indeed for larger models, otherwise sglang crashees with `flashinfer/allocator.h:49: Buffer overflow when allocating memory for batch_prefill_tmp_v with size 2415919104 and alignment 16, but only 2147483648 bytes available in AlignedAllocator. Increase the workspace buffer size.`
  
    
### for long videos: https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.6 
   --json-model-override-args '{"rope_scaling": {"rope_type": "yarn", "factor": 3.0, "original_max_position_embeddings": 262144, "mrope_section": [24, 20, 20], "mrope_interleaved": true}}'

### from qw3.5 card (https://huggingface.co/Qwen/Qwen3.5-2B)

   Long Video Understanding: To optimize inference efficiency for plain text and images, the size parameter in the released video_preprocessor_config.json is conservatively configured. It is recommended to set the longest_edge parameter in the video_preprocessor_config file to 469,762,048 (corresponding to 224k video tokens) to enable higher frame-rate sampling for hour-scale videos and thereby achieve superior performance. For example,

{"longest_edge": 469762048, "shortest_edge": 4096}

Alternatively, override the default values via engine startup parameters. For implementation details, refer to: vLLM / SGLang.
     
---


Give me good command line arguments to start sglang for extracting timecodes of clips from a video with qwen3.x, the output is in json. Also give me good parameters for the corresponding openai-compatible calls to the model.


---

### Temp & top_k tuning

Param tunings for 4 runs on one video with Qwen3.5-2B

```
    "temperature": 0.8,
    "top_p": 0.9,
    "presence_penalty": 1.5,
    "seed": 86,
    "extra_body": {
      "top_k": 20,
      "mm_processor_kwargs": {
        "fps": 2,
        "do_sample_frames": true
      },
      "enable_thinking": false,
      "chat_template_kwargs": {
        "enable_thinking": false
      }
    }
  }
}
```

t=0.5 Avg score: 0.74 over 4 runs
t=0.6 Avg score: 0.79 over 4 runs BEST
t=0.7 Avg score: 0.79 over 4 runs BEST
t=0.8 Avg score: 0.70 over 3 runs
t=0.9 Avg score: 0.62 over 4 runs
t=1.0 Avg score: 0.47 over 3 runs

t=0.6 and...

top_p=0.8 Avg score: 0.79 over 4 runs
top_p=0.9 Avg score: 0.79 over 4 runs
top_p=0.95 Avg score: 0.82 over 4 runs BEST
top_p=1.0 Avg score: 0.76 over 4 runs

!! Best run for 3.5-2B is 46% on sglang, with t=0.6 and top_p=0.95


### deterministic runs w/ seeds
 
python -m sglang.launch_server --model-path Qwen/Qwen3.5-27B --port 8000 --tp-size 1 --mem-fraction-static 0.8 --context-length 49152 --enable-deterministic-inference

Gives me this error: flashinfer/data/include/flashinfer/allocator.h:49: Buffer overflow when allocating memory for batch_prefill_tmp_v with size 2415919104 and alignment 16, but only 2147483648 bytes available in AlignedAllocator. Increase the workspace buffer size.

Brave says:

FlashInfer pre-allocates a fixed-size workspace buffer during initialization based on profiling with small dummy batches.
For large prompts (e.g., >4K tokens), the continuation prefill chunks require significantly more temporary memory (e.g., batch_prefill_tmp_v).
The current workspace is capped at 2147483648 bytes (~2 GB), but the operation needs ~2.42 GB, causing a buffer overflow. 
This issue is closely related to bugs reported in both vLLM and SGLang where workspace sizing is decoupled from --max-num-batched-tokens or --chunked-prefill-size. 

export FLASHINFER_WORKSPACE_SIZE=$((4 << 30))  # 4 GB workspace

python -m sglang.launch_server --model-path Qwen/Qwen3.6-27B --port 8000 --tp-size 1 --mem-fraction-static 0.7 --context-length 49152 --enable-deterministic-inference --reasoning-parser qwen3  --mm-attention-backend fa3 --attention-backend fa3 --keep-mm-feature-on-device

---

Quick comparison of using [] json output, vs {}, vs {reasoning}
With Q3.5-9B

t=1.0 top_p=0.95 fa3 sglang l40s no-reasoning []
Avg score: 0.98 over 2 runs

t=1.0 top_p=0.95 fa3 sglang l40s no-reasoning {}
Avg score: 0.28 over 2 runs

t=1.0 top_p=0.95 fa3 sglang l40s no-reasoning {r}
Avg score: 0.43 over 8 runs

---

### Qwen 35B on HPC...


=> won't work on h100!

I followed the exact same command as recommended by sgand website

https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.6#1-model-introduction

sglang serve --model-path Qwen/Qwen3.6-35B-A3B-FP8 \
  --reasoning-parser qwen3 \
  --mem-fraction-static 0.8
  
Or

sglang serve --model-path Qwen/Qwen3.6-35B-A3B \
  --reasoning-parser qwen3 \
  --mem-fraction-static 0.8

Which is supposed to work on a single H100 ("All Qwen3.6 variants (MoE 35B-A3B and Dense 27B) fit on a single supported GPU at both precisions: [BF16 and FP8 on 80GB+]")

Exception: Capture cuda graph failed: Assertion error (_deps/repo-deepgemm-src/csrc/apis/../jit_kernels/impls/../../jit/compiler.hpp:147): (major > 12 or (major == 12 and minor >= 3)) and "NVCC version should be >= 12.3"

nvcc --version shows 12.2 (cuda 12.2)

---

ML - sg - 3.5 2b

python -m sglang.launch_server --model-path Qwen/Qwen3.5-2B --port 30000 --tp-size 1 --mem-fraction-static 0.8 --context-length 32768 --enable-deterministic-inference --reasoning-parser qwen3  --mm-attention-backend fa3 --attention-backend fa3 --keep-mm-feature-on-device



python -m sglang.launch_server --model-path Qwen/Qwen3.6-27B --port 8000 --tp-size 1 --mem-fraction-static 0.8 --context-length 49152 --enable-deterministic-inference --reasoning-parser qwen3  --mm-attention-backend fa3 --attention-backend fa3 --keep-mm-feature-on-device

## Typology of separators

Separator
    Title card
        Slate (2-pop) https://en.wikipedia.org/wiki/Slate_(broadcasting)
    Color bars https://en.wikipedia.org/wiki/SMPTE_color_bars
    

## Sample videos

NI/S1964_2
NI/55300_A    
NI/DVC43998
    pre: title card (text only)
NI/DVC43313, tricky b/c:
    Two prg, very short one with presenters preparing before going live; then long (~30mins) with actual live show
    The long program contains its own inner title screens
    The separators can be preceded or interrupted by 2-s of footage
    pre: count-down-clock()
NI/90D2335_A
    pre: count-down-clock()
NLW/aobbu34200001
    ini: color bars
    pre: black(1s)+count-down-clock(9s)+black(2s)


sglang w/ Qwen3.5-2B runs OOM on a 24GB VRAM!!!!

sgd --model-path Qwen/Qwen3.5-2B --host 0.0.0.0 --port 30000 --tp-size 1 --mem-fraction-static 0.7 --context-length 20480 --enable-deterministic-inference --reasoning-parser qwen3  --mm-attention-backend fa3 --attention-backend fa3 --keep-mm-feature-on-device --kv-cache-dtype fp8_e4m3

On ml computer

/home/projects/vllm$ vllm serve cyankiwi/Qwen3.5-4B-AWQ-4bit --port 30000 --tensor-parallel-size 1 --max-model-len 32768 --reasoning-parser qwen3 --allowed-local-media-path ~/src/prj/framesense/tests --media-io-kwargs '{"video": {"num_frames": -1}}' --default-chat-template-kwargs '{"enable_thinking": false}' --kv_cache_dtype="fp8"
