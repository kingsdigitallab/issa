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


### Issues

* qwen3.5-2b & 4b models return MM:SS format even when asked for HH:MM:SS; Or return json with start_time instead of startTime.

* qwen3.5-4b can consume a lot of tokens for thinking (5k); not found yet how to disable it via API; this makes it unable to answer the question using the allocated context of 32k.
* `vllm serve Qwen/Qwen3.5-27B-GPTQ-Int4 --port 8000 --tensor-parallel-size 1 --max-model-len 16384 --reasoning-parser qwen3 --allowed-local-media-path $HOME/src/prj/issa/experiments/ --media-io-kwargs '{"video": {"num_frames": -1}}' --default-chat-template-kwargs '{"enable_thinking": false}' --kv_cache_dtype="fp8" --calculate-kv-scales true` doesn't fit into 24GB
* but qwen3.5:27b uses 23GB VRAM with ollama for the same context size; why?
* see unsloth VRAM requirements https://unsloth.ai/docs/models/qwen3.5#usage-guide
* https://docs.vllm.ai/en/stable/features/quantization/gguf/
* https://huggingface.co/collections/Qwen/qwen35
* vLLM: (APIServer pid=3355194) ValueError: GGUF model with architecture qwen35 is not supported yet.
* 9B model still produce incorrect keys in json
* 9B model detects programs and separators for the NLW's sample

## Questions

## TODO

* models: qwen3.5 2b, 4b, *9b, *27b; qwen3.6 27b, (35a3)
* quantised to 4bits
* MTP enabled
* w/ and without reasoning
* kv cache quantised to 8bits (kv_cache_dtype="fp8", or calibrate it)

