# ISSA - MVP 3b

Objectives: test how good recent open-weight vision language models are at producing Audio Descriptions from Horizon 2022 sample clips. Use it as a point of comparison for more specialised AD systems such as DANTE-AD (https://andrewjohngilbert.github.io/DANTE-AD/).

Started: 20/03/2026

Test cases: By The Waters (9m 54s)

## Audio Desc with VLM

### I. AD Generation

#### A. With Qwen 3.5 from frames

#### B. With Qwen 3 or 3.5 from clip

1. try reusing existing scripts or notebook on the HPC
. reproducing old result no longer working, script killed without reason, possibly due to excess memory usage
. 
srun -p interruptible_gpu -c 8 --mem-per-gpu 128G --gpus-per-task 1 --constraint "rtx6000" -n 1 --time 2:00:00 --pty bash

### II. AD Visualisation

#### A Add descriptions on the clip as subtitles.




---

Video Captioning vs Audio Description (from Deganutti & Al poster about DANTE-AD)

Primary purpose:
    Generates a textual description of visual content
    vs
    Provides a spoken narration of key visual elements for accessibility

Target audience 
    Machine learning applications, indexing/search systems
    vs
    Blind or visually impaired audiences
Content focus 
    Visual events, objects, actions 
    vs
    Visual events, objects, actions,scenes, displayed text, mood
Typical length 
    Concise 1-2 sentences 
    vs
    Variable, timed with gaps in dialogue

---
