#!/bin/bash
# Copy all the video files listed in the SAMPLE_FILE
# from the ISSA RDS data folder
# into the current directory.
# Each mp4 file will be copied under a folder of the same name.
# That structure is compatible with FrameSense

SAMPLE_FILE="sample-10.txt"
BASE_DIR="hpc:/rds/prj/dh_issa/data/input/NLS"

# Read the list of relative paths from sample-10.txt
mapfile -t paths < <(grep -v '^#' $SAMPLE_FILE)

# Define the destination directory
DEST_BASE="."

# Create the destination directory if it doesn't exist
# mkdir -p "$dest"

# Loop through each path in the array
for rel_path in "${paths[@]}"; do
    filepath="${BASE_DIR}/${rel_path}"
    full_source="${BASE_DIR}/${rel_path}"

    filename=$(basename "$rel_path")
    folder_name="${filename%.*}"
    dest_dir="${DEST_BASE}/${folder_name}"
    dest_file="${dest_dir}/${filename}"
    
    mkdir -p "$dest_dir"
    scp "$full_source" "$dest_file"
    
    echo "Copied: $filepath"
done
