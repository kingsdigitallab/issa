DEFAULT_FPS="1.5"
DEFAULT_VIDEO_TOKENS="64k"
DEFAULT_SEED="1234"
DEFAULT_REASONING_EFFORT="xhigh"
DEFAULT_VIDEO="839"
DEFAULT_QUESTION="sep1"

FPS="$DEFAULT_FPS"
VIDEO_TOKENS="$DEFAULT_VIDEO_TOKENS"
SEED="$DEFAULT_SEED"
REASONING_EFFORT="$DEFAULT_REASONING_EFFORT"
VIDEO="$DEFAULT_VIDEO"

usage() {
    echo "Usage: $0 [--fps FPS] [--video-tokens VIDEO_TOKENS] [--seed SEED] [--reasoning-effort REASONING_EFFORT]"
    echo "  --fps                 frames per second (default: $DEFAULT_FPS)"
    echo "  --video-tokens        video tokens (default: $DEFAULT_VIDEO_TOKENS)"
    echo "  --seed                seed (default: $DEFAULT_SEED)"
    echo "  --reasoning-effort    reasoning effort (default: $DEFAULT_REASONING_EFFORT)"
    echo "  --video               video name filter (default: $DEFAULT_VIDEO)"
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
        --video)
            VIDEO="$2"
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

ANSWER_SEPARATORS_VLM_MODEL=RedHatAI/Qwen3.8-27B-INT4 \
ANSWER_SEPARATORS_VLM_MAX_TOKENS="30k" \
ANSWER_SEPARATORS_VLM_VIDEO_TOKENS="$VIDEO_TOKENS" \
ANSWER_SEPARATORS_VLM_REASONING_EFFORT="$REASONING_EFFORT" \
ANSWER_SEPARATORS_VLM_MAX_FPS="$FPS" \
ANSWER_SEPARATORS_VLM_SEED="$SEED" \
ANSWER_SEPARATORS_VLM_API_BASE="http://localhost:30000/v1" \
ANSWER_SEPARATORS_VLM_FILTER_QUESTIONS="$DEFAULT_QUESTION" \
FRAMESENSE_DEBUG=1 \
FRAMESENSE_COLLECTIONS="/scratch/prj/dh_issa/issa/workshops/ws1/collections.json" \
./venv/bin/python framesense.py answer_separators_vlm -r  -f "$VIDEO"
