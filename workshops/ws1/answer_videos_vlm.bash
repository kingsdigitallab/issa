DEFAULT_FPS="1"
DEFAULT_VIDEO_TOKENS="64k"
DEFAULT_SEED="43"
DEFAULT_REASONING_EFFORT="xhigh"

FPS="$DEFAULT_FPS"
VIDEO_TOKENS="$DEFAULT_VIDEO_TOKENS"
SEED="$DEFAULT_SEED"
REASONING_EFFORT="$DEFAULT_REASONING_EFFORT"

usage() {
    echo "Usage: $0 [--fps FPS] [--video-tokens VIDEO_TOKENS] [--seed SEED] [--reasoning-effort REASONING_EFFORT]"
    echo "  --fps                 frames per second (default: $DEFAULT_FPS)"
    echo "  --video-tokens        video tokens (default: $DEFAULT_VIDEO_TOKENS)"
    echo "  --seed                seed (default: $DEFAULT_SEED)"
    echo "  --reasoning-effort    reasoning effort (default: $DEFAULT_REASONING_EFFORT)"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fps)
            FPS="$2"
            shift 2
            ;;
        --video-tokens)
            VIDEO_TOKENS="$2"
            shift 2
            ;;
        --seed)
            SEED="$2"
            shift 2
            ;;
        --reasoning-effort)
            REASONING_EFFORT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

cd framesense

ANSWER_VIDEOS_VLM_MODEL=RedHatAI/Qwen3.8-27B-INT4 \
ANSWER_VIDEOS_VLM_MAX_TOKENS="30k" \
ANSWER_VIDEOS_VLM_VIDEO_TOKENS="$VIDEO_TOKENS" \
ANSWER_VIDEOS_VLM_REASONING_EFFORT="$REASONING_EFFORT" \
ANSWER_VIDEOS_VLM_MAX_FPS="$FPS" \
ANSWER_VIDEOS_VLM_SEED="$SEED" \
ANSWER_VIDEOS_VLM_API_BASE="http://localhost:30000/v1" \
ANSWER_VIDEOS_VLM_FILTER_QUESTIONS="prg1" \
FRAMESENSE_DEBUG=1 \
FRAMESENSE_COLLECTIONS="/scratch/prj/dh_issa/issa/workshops/ws1/collections.json" \
./venv/bin/python framesense.py answer_videos_vlm -r -f 234
