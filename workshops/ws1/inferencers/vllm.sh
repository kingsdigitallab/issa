MODEL_NAME="RedHatAI/Qwen3.8-27B-INT4"
CONTEXT="256k"
COLLECTION_PATH=/scratch/prj/dh_issa/issa/workshops/ws1/sample11
SING_FILE="/scratch/prj/dh_issa/sglang/vllm-openai_v0.28.0-cu130.sif"

singularity exec --nv \
    --bind $COLLECTION_PATH:$COLLECTION_PATH \
    --bind $HF_HOME:$HF_HOME \
    $SING_FILE \
    vllm serve $MODEL_NAME \
        --reasoning-parser qwen3 \
        --port 30000 \
        --tensor-parallel-size 1 \
        --mm-encoder-tp-mode data \
        --max-model-len $CONTEXT \
        --allowed-local-media-path "/scratch/prj/dh_issa/issa/workshops/ws1/sample11" \
        --media-io-kwargs '{"video": {"num_frames": -1}}'

# disables the multi-modal processor cache, which prevents the system from caching and re-processing past multi-modal inputs.  This action eliminates the memory overhead associated with the cache (which defaults to 4 GiB), but may result in increased latency for repeated multi-modal processing tasks. 
# --mm-processor-cache-gb 0

