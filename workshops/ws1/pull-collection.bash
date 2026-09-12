#!/bin/bash
# Pull the video batches of one collection from the ISSA HPC workshop
# folder into the local ./batches/ mirror.
# The batch IDs come from a filter in collections-batches.json
# (data[i].attributes.filters), selected with -f <filter>.
# Each <id>/ directory is rsynced with --size-only, so a file is only
# copied when its size differs from the local copy.
# chunks/ folders and .wav files are excluded by default.

# Script created by opencode:e-research/arc:apex
# Prompt summary: new script rsyncing batches/<id>/ dirs from the hpc
# workshop folder into ./batches/, restricted to the IDs of a -f filter
# from collections-batches.json.

BASE_DIR="hpc:/scratch/prj/dh_issa/issa/workshops/ws1/batches"
DEST_DIR="./batches"
COLLECTIONS_FILE="collections-batches.json"
EXCLUDES=(--exclude "chunks/" --exclude "*.wav")

usage() {
    echo "usage: $(basename "$0") -f <filter>" >&2
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

FILTER=""
while getopts ":f:" opt; do
    case $opt in
        f) FILTER="$OPTARG" ;;
        \?) usage; echo "Unknown option: -$OPTARG" >&2; exit 1 ;;
        :) usage; echo "Option -$OPTARG requires an argument" >&2; exit 1 ;;
    esac
done

if [[ -z "$FILTER" ]]; then
    usage
    echo "A filter from $COLLECTIONS_FILE is required, e.g. -f sample11" >&2
    exit 1
fi

if [[ ! -f "$COLLECTIONS_FILE" ]]; then
    echo "$COLLECTIONS_FILE not found (run from the workspace root)" >&2
    exit 1
fi

IDS_STRING="$(get_filter_ids "$FILTER")" || exit 1
IFS='|' read -ra IDS <<< "$IDS_STRING"

mkdir -p "$DEST_DIR"

FAILED=0
for id in "${IDS[@]}"; do
    if rsync -av --size-only "${EXCLUDES[@]}" "${BASE_DIR}/${id}/" "${DEST_DIR}/${id}/"; then
        echo "Copied: ${BASE_DIR}/${id}/"
    else
        echo "FAILED: ${BASE_DIR}/${id}/" >&2
        FAILED=1
    fi
done
exit $FAILED
