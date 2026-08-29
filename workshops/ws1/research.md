Fieldwork log with ideas, issues and observations around the experiments 
to test the performances of programme boundary detection on NLS videos.

Format is quite unstructured. It is mostly for internal purpose with the aim
to reorganise it later into README.md.

We are using Qwen3.x for one-shot detection of programmes in the videos.

# Q&A

Questions we are trying to address via experiments.

One major caveat for the answers below is that the tests are done with a tiny sample and with just a couple of runs per settings. Some answers may be unreliable until we try more repeated experiments. But this can consumes a lot of time.

## Q1. Is reasoning/thinking mode needed?

**Yes**, it consistently increase accuracy (up tp 20%). 

But:
* it takes 2 to 3x longer to complete
* it can sometimes get stuck in excessive thinking 

We've set a limit of 30K tokens for reasoning. Which seems ok in most cases.

## Q2. which Qwen model is best?

In terms of size **27B** is much better than 9B. (2B is useless. 4B is unreliable).

In terms of **version**: 3.5 so far shows better accuracy than 3.6 across a few runs.

**TODO: test more systematically with 3.8.**

Some independent benchmarks show a slight advantage for 3.6 for video understanding.

## Q3. on which GPU can it run?

So far A100, H200, RTX 6000. Qwen 27B, unquantised needs ~80+GB.

## Q4. which inferrence engine works best?

Qwen3.x didn't work with `transformers` API directly at the time of the experiments.

We've tried:
* `vLLM`: works well on KDL machine learning computer (RTX4090) but I had trouble making it work on HPC
* `SGlang`: 0.5.13-cu129 version converted from official dockerfile to singularity works well on a variety of GPUs/nodes on HPC

**TODO**:
* upgrade to SGLang 5.18
* try vllm again

## Q5. how long can the input video be?

No theoretical limit b/c sampling done by Qwen video pre-processor is dynamic.

Presumably there might be a drop in accuracy beyond a certain duration.
**TODO:** But where?

This also depends on the context size, fps, and max pixels.
Not sure exactly how things are calulated (see Q5a).

We've tried 12K and 32K tokens for the video encoding in the context.

Surprisingly 12K had better accuracy over a few experiments.

Note that 32K is our limit within 80-90GB VRAM using SGlang.
The maximum Qwen can process, given enough VRAM, is 224K.

### Q5a. How is the sampling actually happening?

It's quite important to understand how much of the video Qwen "sees". 
For instance if the context is too small, it's likely the fps or downsampling will drop considerably.
If we know the model only sees 1 frame per 10 seconds on a 1h30m video, 
then we better understand the time resolution limitation for the programme detection.
With that information we make more informed decisions about chunk length 
to mitigate fps loss, and/or increased VRAM for addition video context to preserve ~1fps.

See [video preprocessor in sglang](https://github.com/sgl-project/sglang/blob/b647ae82f524ed5e607ac39286ed50ee0b90d023/python/sglang/srt/hardware_backend/npu/modules/qwen_vl_processor.py#L172).

[More info in modelstudio](https://modelstudio.console.alibabacloud.com/ap-southeast-1?spm=a3c0i.28768018.1579141730.1.5cd37661VG9kBj&tab=doc#/doc/?type=model&url=2845871).

**TODO**: I'd like to see what is a the exact fps and frame dimensions used by Qwen
for a given longest_edge, desired fps and input video dimensions & duration.

One way would be to patch the pre-processor to show accurate information at runtime. But not easy in a sif container.

Another would be to ask a coding assistant to build such formula from the pre-processor code source. And have faith in it.

## Q6. which quant is best?

We've tried 27B unquantised (16bits), which runs ok on 80+GB VRAM.

We tried FP8, with apparently less accurate results.

**TODO: try NVP4 and try FP8 again** as they could make room for more video context.

## Q7. what is the accuracy of the programme segmentation task?

It's hard to tell for various reasons:
* our sample contains some trivial cases with a single short program
* the accuracy varies a lot from one run to another (using different random seeds)
* our accuracy metric is quite lenient and needs improvement

With our measurements, the accuracy vary between 70-90%. 

Video 234552207.32 is good case study to get a sense of the capability
because it contains 25 programmes, mostly separated by color bars screen, 
so it's not overly challenging apart from the long duration (109 minutes).

Other videos in the collection can be very challenging 
for any AI tool to segment properly (see error analysis).

## Q8. is it better to prompt for programs or for boundaries?

**Program detection** instructions seems to yield better results.

## Q8. what hasn't been tested?

* accuracy of different quants
* video with subtitles 
* chunking videos
* ...

## Q9. what is the processing speed?

With Qwen-27b, moderate reasoning and 12K video context, programme detection task takes between 1600 and 2500 seconds.

The total duration of our sample of 11 videos is 293 minutes. 

So with that setting, the processing is 7x faster than real time video duration.

Note that there are some caveats to that calculation and other appraoches (chunking or larger video context) could significantly slow things down.

# How to reproduce the experiments

Go to compute node

```bash
srun -p interruptible_gpu -c 8 --mem-per-gpu 16G --gpus-per-task 1 --constraint "rtx6000" -n 1 --time 4:00:00 --pty --exclude erc-hpc-comp[235-239] bash
```

Start model server, SGlang:

```bash
singularity exec --nv --bind /cephfs/volumes/hpc_data_prj/dh_issa/ca337d95-d1b7-4efe-bfd9-6bb60ea0df32/issa/workshops/ws1:/cephfs/volumes/hpc_data_prj/dh_issa/ca337d95-d1b7-4efe-bfd9-6bb60ea0df32/issa/workshops/ws1 --bind $HF_HOME:$HF_HOME /scratch/prj/dh_issa/sglang/sglang_latest.sif sglang serve --reasoning-parser qwen3 --port 30000 --model-path Qwen/Qwen3.8-27B --mem-fraction-static 0.7 --context-length 49152 --attention-backend flashinfer
```

When ready, press CTRL+Z, then type `bg`

Run video Q&A with framesense on HPC:

```bash
cd /scratch/users/k1217897/prj/framesense
. ./venv/bin/activate
ANSWER_VIDEOS_VLM_MAX_TOKENS=30k ANSWER_VIDEOS_VLM_SEED=43 ANSWER_VIDEOS_VLM_THINK="1" ANSWER_VIDEOS_VLM_MODEL=Qwen/Qwen3.8-27B ANSWER_VIDEOS_VLM_API_BASE=http://localhost:30000/v1 ANSWER_VIDEOS_VLM_FILTER_QUESTIONS=programs_3xinc-35-27B-v12k-think-s43 FRAMESENSE_DEBUG=1 FRAMESENSE_COLLECTIONS=/scratch/prj/dh_issa/issa/workshops/ws1/collections.json python framesense.py answer_videos_vlm -f 234 -r
```

Evaluate results:

```bash
/scratch/prj/dh_issa/issa/workshops/ws1$ python eval_segs.py -q programs_3xinc-35-27B-v12k-think-s43 > evals/programs_3xinc-38-27B-v12k-think-s43
```

# Error analysis

## Errors in program boundary detection

`FRAMESENSE_DEBUG=1 FRAMESENSE_COLLECTIONS=/scratch/prj/dh_issa/issa/workshops/ws1/collections.json python framesense.py answer_videos_vlm`

3.6-27b (non-thinking)

### Timing can be a bit approximate on longer videos

e.g. in video 140* vlm finds separator at 31.45 b/w two programs; ground truth is 0.22 - 33.26, 33.26  - 1.01.50

e.g. 234*: all timings are completely wrongs, the video is 1h 49 mins long

Mitigation: use Qwen recommended techniques for long videos

### introduction title and ending credits moved outside prg boundaries

e.g. in video 100* 0.03 -> 2.36 instead of 0.0 -> 2.39 (intro title is removed)

Mitigation: change the prompt to include titles; and redefine the notion of separator

### loose json structure

e.g. in video 260* vlm adds superfluous bbox and label properties

Mitigation: provide example structure in prompt

### internal title (e.g. chapter in doc) misinterpreted as separator

e.g. in video 260* find two programs instead of one, due to internal title: 0.06 -> 5.23 + 5.30 -> 13.47; ground truth is 0.0 -> 13.47

Mitigation: change the prompt to include titles; and redefine the notion of separator

### fade to black treated as prg separator

e.g. in video 828, 2.32 -> 2.35 is a long back screen before end credit. Which is qutie a common practice. But the VLM split that into two programs. Ground truth = 0.0 -> 2.54


### videos

(139* : 0.15 - 5.01, 5.03 - 22.21, 22.23 - 32.27)

103: 
234: 109 mins
911: tricky as there is a (accidental) space between two parts of the same program.

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
        - yet nvidia-smi shows cuda 13... driver is 580.126.20
    - try sglang 0.5.12 with singularity, which contains nvcc 13
        - build singularity sif with `singularity pull docker://lmsysorg/sglang:latest` & copied to HPC
        - singularity exec --nv --bind $HF_HOME:$HF_HOME  --bind ./models:/models   sglang_latest.sif sglang serve --model-path Qwen/Qwen3.6-27B --port 30000 --tp-size 1 --mem-fraction-static 0.7 --context-length 49152 --enable-deterministic-inference --reasoning-parser qwen3  --mm-attention-backend fa3 --attention-backend fa3 --keep-mm-feature-on-device
            + sglang serve --model-path Qwen/Qwen3.5-4B --port 30000 --tp-size 1 --mem-fraction-static 0.7 --context-length 49152 --reasoning-parser qwen3  --enable-flashinfer-allreduce-fusion
            + singularity exec --nv --bind
            + singularity exec --nv --bind /cephfs/volumes/hpc_data_prj/dh_issa/ca337d95-d1b7-4efe-bfd9-6bb60ea0df32/issa/workshops/ws1:/cephfs/volumes/hpc_data_prj/dh_issa/ca337d95-d1b7-4efe-bfd9-6bb60ea0df32/issa/workshops/ws1 --bind $HF_HOME:$HF_HOME /scratch/prj/dh_issa/sglang/sglang_latest.sif sglang serve --model-path Qwen/Qwen3.5-4B --port 30000 --tp-size 1 --mem-fraction-static 0.7 --context-length 49152 --reasoning-parser qwen3 --enable-flashinfer-allreduce-fusion
            + https://github.com/local-inference-lab/rtx6kpro/blob/master/inference-engines/sglang.md#qwen35-397b-fp8-8-gpus

* quantised models
    - python -m sglang.launch_server --model-path Qwen/Qwen3.5-27B-GPTQ-Int4 --port 30000 --tp-size 1 --mem-fraction-static 0.7 --context-length 49152 --enable-deterministic-inference --reasoning-parser qwen3 --mm-attention-backend fa3 --attention-backend fa3 --keep-mm-feature-on-device
        - works at 13.80 tps on a100 80g

* long video support
    - --mm-process-config '{"video": {"size": {"longest_edge": 469762048, "shortest_edge": 4096}}}'
    - that number is for 224k of video frame tokens
    - 2m39s video => 11517 prompt tokens (inc question) => 11517t/3m*60s*2fps = 32t/f
    - 106mins => 13394t =>
    - https://huggingface.co/Qwen/Qwen3.6-27B: Long Video Understanding: To optimize inference efficiency for plain text and images, the size parameter in the released video_preprocessor_config.json is conservatively configured. It is recommended to set the longest_edge parameter in the video_preprocessor_config file to 469,762,048 (corresponding to 224k video tokens) to enable higher frame-rate sampling for hour-scale videos and thereby achieve superior performance. For example
    - 469762048/224/1024 = 2048
    - 25165824 default in video_preprocessor_config.json, patch_size=16 => That's 12k tokens. Which approx matches the number prompt tokens on my experiments.
    - video frame resolution = 768*576
    - 768*576/16/16 = 1728 patches or tokens per frame
    - [video preprocessor in sglang](https://github.com/sgl-project/sglang/blob/b647ae82f524ed5e607ac39286ed50ee0b90d023/python/sglang/srt/hardware_backend/npu/modules/qwen_vl_processor.py#L172)

VLLM_ENABLE_CUDA_COMPATIBILITY=1 singularity exec --nv --bind /cephfs/volumes/hpc_data_prj/dh_issa/ca337d95-d1b7-4efe-bfd9-6bb60ea0df32/issa/workshops/ws1:/cephfs/volumes/hpc_data_prj/dh_issa/ca337d95-d1b7-4efe-bfd9-6bb60ea0df32/issa/workshops/ws1 --bind $HF_HOME:$HF_HOME /scratch/prj/dh_issa/vllm/vllm-openai_latest.sif vllm serve Qwen/Qwen3.6-27B --port 30000 --reasoning-parser qwen3 --max-model-len 49152

{"longest_edge": 469762048, "shortest_edge": 4096}

Alternatively, override the default values via engine startup parameters.

# Engines & models

Docs about running Qwen3.8-27B:

* [Unsloth](https://unsloth.ai/docs/models/qwen3.8#run-qwen3.8-guide)
* [vLLM](https://recipes.vllm.ai/Qwen/Qwen3.8-27B?variant=nvfp4&hardware=b200&features=reasoning%2Cencoder_parallel)
* [HF Qwen3.8 card](https://huggingface.co/Qwen/Qwen3.8-27B-FP8)
* [SGLang](https://lmsysorg.mintlify.app/cookbook/autoregressive/Qwen/Qwen3.8-27B#hw=h200&variant=default&quant=fp8&nodes=single&spec=none&tier=low-latency&ssmDtype=float32)
* [Vram calculator](https://vramcalculator.com/qwen3-8-vram-requirements/)

Q4_K_M -> 64K context on 24GB VRAM

According to that calculator: 262K window requires 36GB at 4bits quant. 30k is used by thinking + response. That leaves 232K for video context which is above the maximum according to Qwen. So in principle a 40+GB VRAM GPU (A40, A100, L40s) should be sufficient for long video processing.

At full precision (16b), the model requires 73GB for 262K window. So why did I find it diffucult to avoid OOM with SGlang at 64K on 80GB VRAM GPU?

## SGlang

I've found it easier to run across different nodes on HPC than vLLM back in June. But harder to tune its VRAM usage.

## vLLM

From SM:

```bash
env VLLM_ENGINE_READY_TIMEOUT_S=3600 \
  /home/xxx/vllm/.venv/bin/vllm serve Qwen/Qwen3.8-27B \
    --served-model-name Qwen3.8-27B-NVFP4 \
    --max-model-len 131072 \
    --quantization fp8 \
    --kv-cache-dtype fp8 \
    --tensor-parallel-size 1 \
    --max-num-seqs 512 \
    --reasoning-parser qwen3 \
    --allowed-local-media-path /home/shihan/storage/video/silence_cut_test \
    --mm-processor-kwargs '{"fps": 2.0, "do_sample_frames": true}' \
    --mm-processor-cache-gb 0 \
    --host 0.0.0.0 \
    --port 8000 \
    --gpu-memory-utilization 0.95
```

NVFP4: 4bits, only for Blackwell GPUs




---
