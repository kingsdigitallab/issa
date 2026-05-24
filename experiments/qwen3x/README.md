## Objectives

Evaluate with metrics how different Qwen3.5 and 3.6 models perform at detecting and locating all programs in a few sample videos.

## Set up

how to start vLLM

```bash
vllm serve Qwen/Qwen3.5-4B --port 8000 --tensor-parallel-size 1 --max-model-len 32768 --reasoning-parser qwen3 --allowed-local-media-path $HOME/src/prj/issa/experiments/ --media-io-kwargs '{"video": {"num_frames": -1}}' --default-chat-template-kwargs '{"enable_thinking": false}' --kv_cache_dtype="fp8"`'
````

## Observations
35 mins video + short prompt take ~15k tokens

Situtation so far:
* 2B is probably not good enough
* 4B will reason beyond 24GB VRAM
* Both don't really follow well the instructed format anyway
* How to run 9B or 27B on 24GB VRAM? vLLM won't run Qwen3.5 GUFF (see below); 27B-FP8 or Int4 is still too onerous at 16k
* => So it looks like we need a larger GPU for processing with 9B & 27B
* => We need to run vLLM on the HPC
* But... cyankiwi/Qwen3.5-9B-AWQ-4bit does seem to work well on 24GB (no reasoning, 23GB VRAM)
* `vllm serve cyankiwi/Qwen3.5-9B-AWQ-4bit --port 8000 --tensor-parallel-size 1 --max-model-len 16384 --reasoning-parser qwen3 --allowed-local-media-path /home/gnoel/src/prj/issa/experiments/ --media-io-kwargs '{"video": {"num_frames": -1}}' --default-chat-template-kwargs '{"enable_thinking": false}' --kv_cache_dtype="fp8"``

## One-page explainer
A single-page interactive with three charts and a table to visualise and communicate experimental results.
To open it, serve from the same directory:

`cd experiments/qwen3x && python -m http.server 8080` and then open
`http://localhost:8080/results.html`

The HTML fetches `evaluations.csv` at runtime. If we add rows to this file, refreshing the page should pick up new data with no HTML edits required.

### Issues
* qwen3.5-2b & 4b models return MM:SS format even when asked for HH:MM:SS; Or return json with start_time instead of startTime.

* qwen3.5-4b can consume a lot of tokens for thinking (5k); not found yet how to disable it via API; this makes it unable to answer the question using the allocated context of 32k.
* this is still an issue with large VRAM, 4B thinking performance look v. good but it never respond within a good number of tokens for the last video
* `vllm serve Qwen/Qwen3.5-27B-GPTQ-Int4 --port 8000 --tensor-parallel-size 1 --max-model-len 16384 --reasoning-parser qwen3 --allowed-local-media-path $HOME/src/prj/issa/experiments/ --media-io-kwargs '{"video": {"num_frames": -1}}' --default-chat-template-kwargs '{"enable_thinking": false}' --kv_cache_dtype="fp8" --calculate-kv-scales true` doesn't fit into 24GB
* but qwen3.5:27b uses 23GB VRAM with ollama for the same context size; why?
* see unsloth VRAM requirements https://unsloth.ai/docs/models/qwen3.5#usage-guide
* https://docs.vllm.ai/en/stable/features/quantization/gguf/
* https://huggingface.co/collections/Qwen/qwen35
* vLLM: (APIServer pid=3355194) ValueError: GGUF model with architecture qwen35 is not supported yet.
* 9B model still produce incorrect keys in json
* 9B model detects programs and separators for the NLW's sample

`python -m sglang.launch_server --model-path Qwen/Qwen3.5-9B --port 8000 --tp-size 1 --mem-fraction-static 0.8 --context-length 32768 --enable-deterministic-inference --reasoning-parser qwen3 --mm-attention-backend fa3 --attention-backend fa3 --keep-mm-feature-on-device ``

* sglang more flexible to install & use across different compute nodes on HPC; also better control of thinking through prompt
* tends to take a lot of VRAM for any model size; not sure yet how to congure that
* but results for the same models are very different than in vLLM runs
* qwen3.6-27B runs on a100_80g but results disappointing and still doesn't return good structure
* sglang produced different outputs for the same seed...
* stopped 3.5-9B from thinking after 5+ minutes...
* awq models don't seem to run on sglang

## Questions

* why is sglang taking same large amount of VRAM for any model?
    * which models could fir on a 24GB or 40GB VRAM card?
* diff b/w presence_penalty and frequency_penalty: (copilot:)
    - Presence penalty — penalizes any token that has appeared at least once. Encourages new topics. (b/w -2 and 2)
    - Frequency penalty — penalizes tokens proportionally to how often they’ve appeared. Reduces repeated wording.

## TODO
* model selection: 
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
    - https://huggingface.co/OpenGVLab/InternVL3-8B (3.5 dowsn't look better on videos according to their own benchmarks)
        - TODO: --enable-multimodal
        - results are poor, also on 3-14B
    - https://huggingface.co/OpenMOSS-Team/MOSS-VL-Instruct-0408
* kv cache quantised to 8bits (kv_cache_dtype="fp8", or calibrate it)
* speed up processing:
    - qwen3.x-35b-a3b (-fp8)
    - --speculative-algorithm EAGLE --speculative-num-steps 3 -speculative-eagle-topk 1 --speculative-num-draft-tokens 4 # https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.6 (MTP)
    - w/ and without reasoning
* reduce amount of reasoning (to keep response within VRAM & reasonable processing time):
    - lower temp???
    - prompt (or system prompt)? Doesn't seem to make any difference with Q3.5
    - 
* reduce VRAM:
    - 4bits quants of model
    - 8bits quants of kv cache. --kv-cache-dtype fp8_e4m3 for low accuracy degradation
* other params:
    - --enable-multimodal # for qwen3-vl? on sglang
    - --mm-attention-backend fa3 --attention-backend fa3 --keep-mm-feature-on-device 
        + that is better indeed for larger models, otherwise sglang crashees with `flashinfer/allocator.h:49: Buffer overflow when allocating memory for batch_prefill_tmp_v with size 2415919104 and alignment 16, but only 2147483648 bytes available in AlignedAllocator. Increase the workspace buffer size.`
  
    
## for long videos: https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.6 
   --json-model-override-args '{"rope_scaling": {"rope_type": "yarn", "factor": 3.0, "original_max_position_embeddings": 262144, "mrope_section": [24, 20, 20], "mrope_interleaved": true}}'

## from qw3.5 card (https://huggingface.co/Qwen/Qwen3.5-2B)

   Long Video Understanding: To optimize inference efficiency for plain text and images, the size parameter in the released video_preprocessor_config.json is conservatively configured. It is recommended to set the longest_edge parameter in the video_preprocessor_config file to 469,762,048 (corresponding to 224k video tokens) to enable higher frame-rate sampling for hour-scale videos and thereby achieve superior performance. For example,

{"longest_edge": 469762048, "shortest_edge": 4096}

Alternatively, override the default values via engine startup parameters. For implementation details, refer to: vLLM / SGLang.
     
---


Give me good command line arguments to start sglang for extracting timecodes of clips from a video with qwen3.x, the output is in json. Also give me good parameters for the corresponding openai-compatible calls to the model.


---


Param tunings for 4 runs on one video with Qwen3.5-2B

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


# 
python -m sglang.launch_server --model-path Qwen/Qwen3.5-27B --port 8000 --tp-size 1 --mem-fraction-static 0.8 --context-length 49152 --enable-deterministic-inference

Gives me this error: flashinfer/data/include/flashinfer/allocator.h:49: Buffer overflow when allocating memory for batch_prefill_tmp_v with size 2415919104 and alignment 16, but only 2147483648 bytes available in AlignedAllocator. Increase the workspace buffer size.

Brave says:

FlashInfer pre-allocates a fixed-size workspace buffer during initialization based on profiling with small dummy batches.
For large prompts (e.g., >4K tokens), the continuation prefill chunks require significantly more temporary memory (e.g., batch_prefill_tmp_v).
The current workspace is capped at 2147483648 bytes (~2 GB), but the operation needs ~2.42 GB, causing a buffer overflow. 
This issue is closely related to bugs reported in both vLLM and SGLang where workspace sizing is decoupled from --max-num-batched-tokens or --chunked-prefill-size. 

export FLASHINFER_WORKSPACE_SIZE=$((4 << 30))  # 4 GB workspace

