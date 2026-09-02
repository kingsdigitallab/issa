# Notebook

```bash
python -m venv venv
. venv/bin/activate
pip install -r requirements.txt
python -m jupyter lab
```

# Video pre-processing on HPC

If not already there, place the sample videos under sample11/X.32/X.32.mp4. Where X is the first column in sample-11.csv. `copy-videos.bash` will help you with copying the video over.

```bash
# start the vLLM server:
./inferencers/vllm.sh

# run FrameSense answer_videos_vlm operator on the NLS sample:
./answer_videos_vlm.bash
```

# Scripts

- `copy-videos.bash`: Copy the sample videos listed in `sample-11.txt` from the ISSA RDS data folder into `sample11/`
- `batches/vid-watcher.py`: Watch the current folder and compress every new `X.mp4` landing in it into `X/X.mp4`, removing the original on success (ffmpeg via the FrameSense singularity image)
- `inferencers/vllm.sh`: Launch the vLLM server (Qwen3.8-27B-INT4, 256k context) with the diagnostic patches bind-mounted
- `inferencers/vllm-patches/`: Diagnostic `[VIDEO DEBUG]` patches bind-mounted over the SIF's vLLM files (see its README)
- `answer_videos_vlm.bash`: Answer the programme questions on the NLS videos via the running server (`--fps`, `--video-tokens`, `--seed`, `--reasoning-effort`)
- `multi_answer.py`: Run `answer_videos_vlm.bash` then `cp_answer.py` for every fps × video-tokens combination
- `cp_answer.py`: Copy the latest video answer into the aggregated `evals/video_answers.json`
- `encode_prompt.py`: Convert a prompt string into the params.json JSON format
- `segments.py`: Segment helpers (load/compare/validate) shared by the eval scripts
- `extract_segments.py`: Draft true programme segments from the model predictions, for manual verification
- `eval_segs.py`: Score predicted segments against `segments_true/`
- `evals/viz.py`: Render an SVG timeline of programme intervals for one video as a stack of four bands: ground mid-frames, ground segments, ground gap mid-frames, predicted segments (run from the repo root, e.g. `venv/bin/python evals/viz.py prg1 139329389.32`)
- `qwen3_video_sampling.py`: Simulate Qwen3.8 video sampling in vLLM (fps, frame count, resolution) for planning settings
