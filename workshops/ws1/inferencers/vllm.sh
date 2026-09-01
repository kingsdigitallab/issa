MODEL_NAME="RedHatAI/Qwen3.8-27B-INT4"
CONTEXT="256k"
COLLECTION_PATH=/scratch/prj/dh_issa/issa/workshops/ws1/sample11
SING_FILE="/scratch/prj/dh_issa/sglang/vllm-openai_v0.28.0-cu130.sif"
# 224k video tokens max as explained on Qwen3.x model cards, see longest_edge
# ((224 * 1024 = 229376))
# 268435456 = 128k video context = 128 * 1024 * 2048 # tested ok
# 298450944 = 144k # 331612160 = 160k # 397934592 = 192k # 431095808 = 208k
PATCH_DIR=/scratch/prj/dh_issa/issa/workshops/ws1/inferencers/vllm-patches

SINGULARITYENV_VLLM_LOGGING_LEVEL=DEBUG \
SINGULARITYENV_VLLM_DEBUG_LOG_API_SERVER_RESPONSE=TRUE \
singularity exec --nv \
    --bind $PATCH_DIR/vllm/multimodal/video.py:/usr/local/lib/python3.12/dist-packages/vllm/multimodal/video.py \
    --bind $PATCH_DIR/vllm/multimodal/media/video.py:/usr/local/lib/python3.12/dist-packages/vllm/multimodal/media/video.py \
    --bind $PATCH_DIR/vllm/model_executor/models/qwen3_vl.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/qwen3_vl.py \
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
        --allowed-local-media-path "/scratch/prj/dh_issa/issa/workshops/ws1/sample11" \
        --enable-chunked-prefill --max-num-batched-tokens 4096 \
        --mm-processor-kwargs '{"size": {"longest_edge": 298450944, "shortest_edge": 4096}, "max_frames": 8100}' \
        --limit-mm-per-prompt '{"image": 0, "video": 1}' \
        --skip-mm-profiling \
        --mm-processor-cache-gb 0 \
        --gpu-memory-utilization 0.70 \
        --media-io-kwargs '{"video": {"num_frames": -1}}'

# disables the multi-modal processor cache, which prevents the system from caching and re-processing past multi-modal inputs.  This action eliminates the memory overhead associated with the cache (which defaults to 4 GiB), but may result in increased latency for repeated multi-modal processing tasks. 
# --mm-processor-cache-gb 0 # from sm
# --mm-encoder-tp-mode data \ # not needed for 1 GPU 
# Below were useless sugegstion by Gemini to increase the hard-coded limit of 16k for the media context
# --limit-mm-per-prompt '{"video": 10}' \ # useless
# --limit-mm-per-prompt '{"video": 4}' \  # useless
# --max-num-batched-tokens 32768 \ # useless
# --limit-mm-per-prompt '{"video": {"count": 1, "max_pixels": 12845056}}' \
#
# From GLM:
# Add two flags to your vllm serve command:
# --mm-processor-kwargs '{"size": {"longest_edge": 469762048, "shortest_edge": 4096}}' \
# --limit-mm-per-prompt '{"image": 0, "video": 1}' \
# How it works: The flat size raises the video budget to ~229K tokens at startup. The flat form also leaks into the image budget (~458K), but setting image: 0 prevents image dummy profiling, so the encoder cache is sized based on the video budget only (229K >> your 18432).
# Pros: CLI-only, no file edits, works on v0.28.0.
# Cons: Disables image processing entirely while active. Startup profiling processes a ~229K-token video dummy through the vision encoder (may take a few minutes). If boot aborts with a processor cache error, also add --mm-processor-cache-gb 0.
# 
# ---
#
# The EngineCore process was killed by signal -9 (SIGKILL, typically the OOM killer). Here's what happened:
# Diagnosis
# The log confirms the encoder cache was correctly sized:
# Encoder cache will be initialized with a budget of 229376 tokens, and profiled with 1 video items of the maximum feature size.
# Then profiling began — vLLM attempted to push a dummy 229K-token video through the vision encoder to measure activation memory. With longest_edge=469762048, the raw pixel data alone is ~5.6 GB (470M pixels × 3 channels × 4 bytes), plus the vision encoder activations on top. After loading model weights (17.78 GiB), the remaining GPU or system RAM was insufficient, and the process was killed.
# Proposed Fix
# Add two more flags to the launch command:
# Flag
# --skip-mm-profiling
# --mm-processor-cache-gb 0
# Trade-off of --skip-mm-profiling: vLLM won't know how much GPU memory to reserve for encoder activations, so it may over-allocate KV cache. If you get runtime OOM when processing a large video, add --gpu-memory-utilization 0.85 (or lower) to leave headroom.
# The full set of new/changed flags would be:
# --mm-processor-kwargs '{"size": {"longest_edge": 469762048, "shortest_edge": 4096}}' \
# --limit-mm-per-prompt '{"image": 0, "video": 1}' \
# --skip-mm-profiling \
# --mm-processor-cache-gb 0 \
#
# Still OOM at startup due to dummy video pre-processing => Apex recommends lowering longest_edge to 268435456 (128k video tokens)
#
# --gpu-memory-utilization 0.70 is s good choice on A100 80g for our settings
# Recommendation from GLM: 
# When to change it
# - 0.75 — only if you later need many concurrent long-context requests (KV pressure).
# - 0.65 — if you push longest_edge toward 224k+ and see runtime encoder OOM.
# - Don't exceed 0.80 (docs/04's tradeoff table: headroom drops to 15.85 GiB, which fails the 1.5x-safety test for the 224K encoder).
