#!/bin/bash
# Script created by opencode:e-research/arc:apex
# Creates the pocket folder and compresses every sample11/X/X.mp4 into
# pocket/X.pocket.mp4 with ffmpeg (480x360, ultrafast, crf 38, 32k mono AAC).

DEFAULT_SAMPLE_DIR="sample11"
DEFAULT_POCKET_DIR="sample11/pocket"

FFMPEG_PRESET="ultrafast"
FFMPEG_CRF="32" # 38 quite poor but tiny; 32: 2x the size; 28: 3x the size
FFMPEG_SCALE="480:360"
AUDIO_CODEC="aac"
AUDIO_BITRATE="32k"
AUDIO_CHANNELS="1"

INTERRUPT_EXIT_CODE="130"

SAMPLE_DIR="$DEFAULT_SAMPLE_DIR"
POCKET_DIR="$DEFAULT_POCKET_DIR"

usage() {
    echo "Usage: $0 [--sample-dir SAMPLE_DIR] [--pocket-dir POCKET_DIR]"
    echo "  --sample-dir    folder containing the X/X.mp4 files (default: $DEFAULT_SAMPLE_DIR)"
    echo "  --pocket-dir    destination folder for the compressed files (default: $DEFAULT_POCKET_DIR)"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --sample-dir)
            SAMPLE_DIR="$2"
            shift 2
            ;;
        --pocket-dir)
            POCKET_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

# Quit once the user presses Ctrl+C (the running ffmpeg is given a chance
# to finalise its output file first)
trap 'echo "Interrupted, quitting" >&2; exit $INTERRUPT_EXIT_CODE' INT

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "Error: ffmpeg not found in PATH" >&2
    exit 1
fi

if [[ ! -d "$SAMPLE_DIR" ]]; then
    echo "Error: folder not found: $SAMPLE_DIR" >&2
    exit 1
fi

mkdir -p "$POCKET_DIR" || exit 1

POCKET_ABS="$(realpath -m "$POCKET_DIR")"

# Collect every X/X.mp4, ignoring the pocket folder itself
sources=()
for dir in "$SAMPLE_DIR"/*/; do
    [[ -d "$dir" ]] || continue
    [[ "$(realpath -m "$dir")" == "$POCKET_ABS" ]] && continue
    X="$(basename "$dir")"
    [[ -f "$SAMPLE_DIR/$X/$X.mp4" ]] && sources+=("$SAMPLE_DIR/$X/$X.mp4")
done

total="${#sources[@]}"
if [[ $total -eq 0 ]]; then
    echo "No X/X.mp4 files found under $SAMPLE_DIR" >&2
    exit 1
fi

i=0
ok=0
fail=0
for src in "${sources[@]}"; do
    i=$((i + 1))
    X="$(basename "$(dirname "$src")")"
    out="$POCKET_DIR/$X.pocket.mp4"
    echo "[$i/$total] Compressing $X ..."
    if ffmpeg -y -i "$src" \
        -c:v libx264 -preset "$FFMPEG_PRESET" -crf "$FFMPEG_CRF" \
        -vf "scale=$FFMPEG_SCALE" \
        -c:a "$AUDIO_CODEC" -b:a "$AUDIO_BITRATE" -ac "$AUDIO_CHANNELS" \
        -movflags +faststart \
        "$out"; then
        ok=$((ok + 1))
    else
        fail=$((fail + 1))
        echo "[$i/$total] FAILED: $src" >&2
    fi
done

echo "Compressed $ok/$total videos into $POCKET_DIR ($fail failed)"
if [[ $fail -gt 0 ]]; then
    exit 1
fi
