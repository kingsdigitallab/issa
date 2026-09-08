#!/bin/bash

#SBATCH --partition=interruptible_gpu
#SBATCH --cpus-per-task=10
#SBATCH --ntasks=1
#SBATCH --mem=40G
#SBATCH --time=04:00:00
#SBATCH --constraint "l40s"

cd /scratch/prj/dh_issa/issa/workshops/ws1/framesense
FRAMESENSE_COLLECTIONS=/scratch/prj/dh_issa/issa/workshops/ws1/collections-batches.json ./venv/bin/python framesense.py run_pipeline -k

