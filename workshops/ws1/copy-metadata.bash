#!/bin/bash
# Copy the NLS metadata spreadsheets (CSV form)
# from the ISSA RDS data folder
# into the local mirror of that same RDS tree.
# Mirrors copy-videos.bash: same RDS mount, same credential model.

BASE_DIR="hpc:/rds/prj/dh_issa/data/input/NLS/batch2/NLS Metadata"
DEST_DIR="../../data/input/NLS/batch2/NLS Metadata"

# The relational export FILMS.xlsx joins to via ref no, plus its
# lookup/junction tables. CSV is the preferred, already-converted
# form on the RDS share (same filenames, .csv instead of .xlsx).
FILES=(
    "FILMS.csv"
    "Clips_Table.csv"
    "GENRE.csv"
    "SERIES.csv"
    "PERSONALITIES.csv"
    "SPECIFIC_CATEGORIES.csv"
    "FILM_GENRE_ASSIGN.csv"
    "FILM_SERIES_ASSIGN.csv"
    "FILM_PERSONALITY_ASSIGN.csv"
    "FILM_CATEGORY_ASSIGN.csv"
    "annotatedschema.csv"
)

mkdir -p "$DEST_DIR"

for f in "${FILES[@]}"; do
    full_source="${BASE_DIR}/${f}"
    dest_file="${DEST_DIR}/${f}"

    rsync -av --size-only "$full_source" "$dest_file"

    echo "Copied: $full_source"
done
