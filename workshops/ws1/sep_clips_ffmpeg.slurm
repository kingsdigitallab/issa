#!/bin/bash

#SBATCH --partition=cpu
#SBATCH --cpus-per-task=8
#SBATCH --ntasks=1
#SBATCH --mem=8G
#SBATCH --time=04:00:00
##2SBATCH --constraint "a100_80g"
##2SBATCH --reservation "rental_15211"

filter="${1:-1}"
echo "filter = $filter"

cd /scratch/prj/dh_issa/issa/workshops/ws1/framesense
FRAMESENSE_COLLECTIONS=/scratch/prj/dh_issa/issa/workshops/ws1/collections-batches.json ./venv/bin/python framesense.py separate_clips_ffmpeg -e "full.mp4" -f "/$filter"
# FRAMESENSE_COLLECTIONS=/scratch/prj/dh_issa/issa/workshops/ws1/collections-batches.json ./venv/bin/python framesense.py run_pipeline -k --filter='-full.'

