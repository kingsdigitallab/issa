#!/bin/bash

#SBATCH --partition=cpu
#SBATCH --cpus-per-task=18
#SBATCH --ntasks=1
#SBATCH --mem=8G
#SBATCH --time=21:00:00
#SBATCH --output=vid-watcher-out.txt           # Standard output file
#SBATCH --error=vid-watcher-err.txt             # Standard error file

python3 vid-watcher.py   

