#!/bin/bash
#SBATCH --job-name="vid-watcher-$ISSA_PART"
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --mem=4G
#SBATCH --time=4:00:00
#SBATCH --output=vid-watcher-job-%j.out
#SBATCH --error=vid-watcher-job_%j.err

python vid-watcher.py -f $ISSA_PART --once

