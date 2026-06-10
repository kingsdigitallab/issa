

- answer_videos_qwen3vl] w/ "Qwen/Qwen3-VL-32B-Instruct is OOM on RTX6000 (97GB VRAM)


# Issues

## Making FS work with SGLang on HPC nodes

Summary: so far the Qwen models only work on a100_80g. Which is not always available on HPC.

Issues:

* known issue: qwen3-vl-32B-instruct runs OOM when called from FrameSense answer_videos_qwen3vl. A h100 should be sufficient for 30mins videos.
* FS answer_videos_vlm on a100_80g with sglang & qwen3.6-27B often returns no answer to the question. That set up was tested extensively in experiments/qwen3x/vqa.py so it should work. Needs debugging.
    * could be limitation in context or max new tokens
    * could be an error in the formatting of the json in the output
    
* why is token/s so slow on a100_80g? 8.15 for qwen3.6-27B - But SGlang can't work with GGUF, and Ampere don't work with FP8.

* 27b not working on h100, but same config works on a100_80g
    - RuntimeError: DeepGEMM failed for matrix shapes M=14, N=10240, K=5120. This typically occurs when dimensions are too small for DeepGEMM's TMA descriptors. Consider increasing MIN_DEEPGEMM_DIM in matmul_persistent() or disabling DeepGEMM for small matrices. Original error: Assertion error (_deps/repo-deepgemm-src/csrc/apis/../jit_kernels/impls/../../jit/compiler.hpp:147): (major > 12 or (major == 12 and minor >= 3)) and "NVCC version should be >= 12.3"
    - nvcc & cuda 12.2 on h100 node, driver 535.309.01
    - driver on 80g is 535.288.01, cuda/nvcc is exact same version 12.2
    - reinstalling sglang on the h100 node as described by sglang doc and lanching the server lead to an error with 

* 27b spread over 4 x l40s misbehave with normal settings; it returns just a few random characters

* rtx6000: 
    - 3.5-27B
        - fa3 not supported by Blackwell => fa4
        - fa4 not supported for deterministic inferrence => remove deterministic inferrence
        - "AssertionError: triton or trtllm_mha backend are the only supported backends on Blackwell GPUs for hybrid GDN models, use --attention-backend triton or --attention-backend trtllm_mha to specify the backend" => leave unspecified
        - When using triton attention by default, sglang will OOM on the 27B model
        - python -m sglang.launch_server --model-path Qwen/Qwen3.5-27B --port 30000 --tp-size 1 --mem-fraction-static 0.7 --context-length 49152 --reasoning-parser qwen3 --attention-backend triton
            - ^ works... at 23tps
            - but accuracy is terrible
    - 3.6-27B 
        - Error: Capture cuda graph failed: DeepGEMM failed for matrix shapes M=16, N=10240, K=5120. This typically occurs when dimensions are too small for DeepGEMM's TMA descriptors. Consider increasing MIN_DEEPGEMM_DIM in matmul_persistent() or disabling DeepGEMM for small matrices. Original error: Assertion error (_deps/repo-deepgemm-src/csrc/apis/gemm.hpp:390): Unsupported architecture
    - 3.5-27B-FP8:
        - Error: major > 12 or (major == 12 and minor >= 3)) and "NVCC version should be >= 12.3"
        - nvcc on erc-hpc-comp242 is Cuda compilation tools, release 12.2, V12.2.128; Build cuda_12.2.r12.2/compiler.33053471_0
        - yet nvidia-smi shows cuda 13...


* quantised models
    - python -m sglang.launch_server --model-path Qwen/Qwen3.5-27B-GPTQ-Int4 --port 30000 --tp-size 1 --mem-fraction-static 0.7 --context-length 49152 --enable-deterministic-inference --reasoning-parser qwen3 --mm-attention-backend fa3 --attention-backend fa3 --keep-mm-feature-on-device
        - works at 13.80 tps

## Errors in program boundary detection

`FRAMESENSE_DEBUG=1 FRAMESENSE_COLLECTIONS=/scratch/prj/dh_issa/issa/workshops/ws1/collections.json python framesense.py answer_videos_vlm`

3.6-27b (non-thinking)

### Timing can be a bit approximate on longer videos

e.g. in video 140* vlm finds separator at 31.45 b/w two programs; ground truth is 0.22 - 33.26, 33.26  - 1.01.50

e.g. 234*: all timings are completely wrongs, the video is 1h 49 mins long

Mitigation: use Qwen recommended techniques for long videos

### introduction title and ending credits moved outside prg boundaries

e.g. in video 100* 0.03 -> 2.36 instead of 0.0 -> 2.39 (intro title is removed)

Mitigation: change the prompt to include titles; and redifine the notion of separator

### loose json structure

e.g. in video 260* vlm adds superfluous bbox and label properties

Mitigation: provide example structure in prompt

### internal title (e.g. chapter in doc) misinterpreted as separator

e.g. in video 260* find two programs instead of one, due to internal title: 0.06 -> 5.23 + 5.30 -> 13.47; ground truth is 0.0 -> 13.47

Mitigation: change the prompt to include titles; and redefine the notion of separator

### fade to black treated as prg separator

e.g. in video 828, 2.32 -> 2.35 is a long back screen before end credit. Which is qutie a common practice. But the VLM split that into two programs. Ground truth = 0.0 -> 2.54


---

139* : 0.15 - 5.01, 5.03 - 22.21, 22.23 - 32.27

# videos

103: 
234: 109 mins
911: tricky as there is a (accidental) space between two parts of the same program.

    