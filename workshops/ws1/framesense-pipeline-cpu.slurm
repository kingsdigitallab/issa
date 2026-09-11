#!/bin/bash

#SBATCH --partition=cpu
#SBATCH --cpus-per-task=12
#SBATCH --ntasks=1
#SBATCH --mem=12G
#SBATCH --time=04:00:00

cd /scratch/prj/dh_issa/issa/workshops/ws1/framesense
FRAMESENSE_COLLECTIONS=/scratch/prj/dh_issa/issa/workshops/ws1/collections-batches.json ./venv/bin/python framesense.py run_pipeline -k --filter='-full.'


