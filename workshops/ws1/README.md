This is a technical document for the processing of WS1 with National Library of Scotland. 

For a summary of the workshop see the [WS1 ISSA wiki page](https://github.com/kingsdigitallab/issa/wiki/WS1-%E2%80%95National-Library-of-Scotland). 
For a high-level analysis of the outputs see [this interactive analysis page](https://kingsdigitallab.github.io/issa/workshops/ws1/issa_ws1.html). 
For a rigorous quantitative evaluation on a subset of annotated examples see [this file](https://github.com/kingsdigitallab/issa/blob/main/workshops/ws1/catalogue/eval_predictions_v2.py).

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

# Metadata

The NLS metadata (FILMS, Clips_Table, and their genre/series/personality/category
lookup tables) lives on the ISSA RDS share, mirrored locally under
`<repo-root>/data/input/NLS/batch2/NLS Metadata/` (gitignored). `copy-metadata.bash`
pulls it down; `notebooks/nls_metadata_analysis.ipynb` joins it into one dataframe
and reproduces the structural findings behind "programme = tape" vs "programme =
shotlist item" and the "compilation" ambiguity. It builds on the descriptive stats and `sample-11.csv` generation already in `batch_analysis.ipynb`.

# Scripts

- `copy-videos.bash`: Copy the sample videos listed in `sample-11.txt` from the ISSA RDS data folder into `sample11/`
- `copy-metadata.bash`: Copy the NLS metadata CSVs from the ISSA RDS data folder into `<repo-root>/data/input/NLS/batch2/NLS Metadata/`
- `batch_analysis.ipynb`: Merge FILMS + Clips_Table, descriptive stats (duration/year/type distributions), and generates `sample-11.csv`
- `notebooks/nls_metadata_analysis.ipynb`: Full relational join of all NLS metadata tables; reproduces the shotlist-timecode and "compilation" language findings; NLS review worklist; exports `metadata_hierarchy_data.json` for the dashboard below
- `notebooks/predictions_analysis.ipynb`: First look at the pipeline output (`kdl-metadata-385.v2(predictions-385.csv`, one row per predicted programme): cleaning audit, descriptive stats, charts, a ranked human watching list (also exported as a git-ignored spreadsheet under `<repo-root>/data/output/ws1/`), and an aggregates-only export `issa_ws1_predictions.json`
- `issa_ws1.html` / `issa_ws1_predictions.json`: Workshop 1 explainer page (Chart.js; served via GitHub Pages like the other pages). Reads `metadata_hierarchy_data.json` (NLS catalogue aggregates) plus `issa_ws1_predictions.json` (pipeline aggregates) — no model-written text about individual films. For the next workshop copy it to `issa_wsN.html`, re-run the notebooks and edit the prose
- `metadata_hierarchy.html` / `metadata_hierarchy_data.json`: Public dashboard (styled like `experiments/qwen3x/results.html`, served the same way via GitHub Pages) — the archive → collection → video file → programme → segment hierarchy, toggled between "as received from NLS" and "+ our analysis". Duplicate this pair per workshop as the data changes
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
- `evals/viz.py`: Render an SVG timeline of programme intervals for one video as a stack of five bands: ground mid-frames, ground segments, ground gap mid-frames (red border = undetected gap), false predictions gap mid-frames, predicted segments (run from the repo root, e.g. `venv/bin/python evals/viz.py prg1 139329389.32`)
- `qwen3_video_sampling.py`: Simulate Qwen3.8 video sampling in vLLM (fps, frame count, resolution) for planning settings
