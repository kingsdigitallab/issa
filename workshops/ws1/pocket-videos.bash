#!/bin/bash
# Script created by opencode:e-research/arc:apex
# Creates the pocket folder and compresses every video matching a required
# -f/--filter filter into pocket/X.pocket.mp4 with ffmpeg (480x360,
# ultrafast, crf 32, 32k mono AAC). The filter is a pipe-separated batch ID
# list read from data[i].attributes.filters in collections.json; matching
# videos (basename containing one of the IDs) are searched recursively
# anywhere under --sample-dir.
# Prompt summary: take a required filter argument, look it up in
# collections.json, then compress only the matching videos, found anywhere
# under the sample dir rather than only as X/X.mp4.

DEFAULT_SAMPLE_DIR="batches"
DEFAULT_POCKET_SUBDIR="pocket"

FFMPEG_PRESET="ultrafast"
FFMPEG_CRF="32" # 38 quite poor but tiny; 32: 2x the size; 28: 3x the size
FFMPEG_SCALE="480:360"
AUDIO_CODEC="aac"
AUDIO_BITRATE="32k"
AUDIO_CHANNELS="1"

COLLECTIONS_FILE="collections.json"

INTERRUPT_EXIT_CODE="130"

SAMPLE_DIR="$DEFAULT_SAMPLE_DIR"
POCKET_DIR=""
FILTER=""

usage() {
    echo "Usage: $0 -f <filter> [--sample-dir SAMPLE_DIR] [--pocket-dir POCKET_DIR]"
    echo "  -f, --filter    filter key of data[i].attributes.filters in $COLLECTIONS_FILE (e.g. sample11)"
    echo "  --sample-dir    folder searched recursively for the filter videos (default: $DEFAULT_SAMPLE_DIR)"
    echo "  --pocket-dir    destination folder for the compressed files (default: $DEFAULT_POCKET_SUBDIR)"
}

# Print the pipe-separated ID string of the given filter from
# $COLLECTIONS_FILE, or fail with the list of available filters.
get_filter_ids() {
    local filter="$1"
    python3 -c '
import json, sys

with open(sys.argv[1]) as f:
    data = json.load(f)["data"]
name = sys.argv[2]
for entry in data:
    ids = entry.get("attributes", {}).get("filters", {}).get(name)
    if ids is not None:
        print(ids)
        break
else:
    available = sorted({k for e in data for k in e.get("attributes", {}).get("filters", {})})
    names = ", ".join(available)
    print(f"Unknown filter: {name}. Available filters: {names}", file=sys.stderr)
    sys.exit(1)
' "$COLLECTIONS_FILE" "$filter"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--filter)
            FILTER="$2"
            shift 2
            ;;
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

if [[ -z "$FILTER" ]]; then
    usage
    echo "A filter from $COLLECTIONS_FILE is required, e.g. -f sample11" >&2
    exit 1
fi

if [[ ! -f "$COLLECTIONS_FILE" ]]; then
    echo "$COLLECTIONS_FILE not found (run from the workspace root)" >&2
    exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "Error: ffmpeg not found in PATH" >&2
    exit 1
fi

if [[ ! -d "$SAMPLE_DIR" ]]; then
    echo "Error: folder not found: $SAMPLE_DIR" >&2
    exit 1
fi

IDS_STRING="$(get_filter_ids "$FILTER")" || exit 1
IFS='|' read -ra IDS <<< "$IDS_STRING"

# Pocket folder defaults to a subfolder of the sample dir
[[ -z "$POCKET_DIR" ]] && POCKET_DIR="$DEFAULT_POCKET_SUBDIR"

mkdir -p "$POCKET_DIR" || exit 1

SAMPLE_ABS="$(realpath -m "$SAMPLE_DIR")"
POCKET_ABS="$(realpath -m "$POCKET_DIR")"

# Collect, for every filter ID, every video whose basename contains it,
# anywhere under SAMPLE_DIR; ignore the pocket folder itself and any
# earlier pocket output
sources=()
for id in "${IDS[@]}"; do
    [[ -n "$id" ]] || continue
    while IFS= read -r -d '' src; do
        sources+=("$src")
    done < <(find "$SAMPLE_ABS" -type f -name "*${id}*.mp4" \
        ! -name "*.pocket.mp4" -not -path "$POCKET_ABS/*" -print0 | sort -z)
done

total="${#sources[@]}"
if [[ $total -eq 0 ]]; then
    echo "No videos matching filter '$FILTER' found under $SAMPLE_DIR" >&2
    exit 1
fi

i=0
ok=0
fail=0
skip=0
declare -A queued=()
for src in "${sources[@]}"; do
    i=$((i + 1))
    X="$(basename "$src" .mp4)"
    out="$POCKET_DIR/$X.pocket.mp4"
    if [[ -n "${queued[$out]}" ]]; then
        skip=$((skip + 1))
        echo "[$i/$total] SKIPPED: $src (same output name as an earlier video)" >&2
        continue
    fi
    queued[$out]=1
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

echo "Compressed $ok/$total videos into $POCKET_DIR ($fail failed, $skip skipped)"
if [[ $fail -gt 0 ]]; then
    exit 1
fi
