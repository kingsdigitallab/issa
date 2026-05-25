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
