This is a technical document for the processing of WS2 with the North West Film Archive (NWFA)
and Yorkshire Film Archive (YFA), the combined northern England trip of 3–5 November 2026.
This README currently covers the **NWFA** strand.

For a high-level analysis of the outputs see
[this interactive analysis page](https://kingsdigitallab.github.io/issa/workshops/ws2/issa_ws2_nwfa.html).

Built on the same pattern as [WS1 / NLS](../ws1/README.md): a generator script produces
aggregate JSON, a single static page reads it. The page is **not** edited between runs —
re-run the generator and the numbers, charts and stage badge all update.

# The material

NWFA shared 400 video files in two batches of 200, which are near-opposites as segmentation
problems.

| | Channel M (H22) | Film & Video catalogue |
|---|---|---|
| Metadata file | `Channel M ISSA.xlsx` | `ISSA FV Cat data.xlsx` |
| Filename column | `BX` / "File name" (does not match content — see below) | `CS` / "Filename" |
| Folder on the drive | `/H22` | `/ISSA FV content` |
| Quantity | 200 | 200 |
| Columns populated | 17 of 77 | 87 of 97 (20 complete) |
| Descriptive metadata | **none** — every descriptive column is empty for all 200 records | synopsis, index terms, category, year, colour, sound, duration, producer, place |
| Est. duration | ~150–200 hrs (no durations in the metadata) | 43.7 hrs |

**The Channel M label problem.** A printing error on the barcodes means the label
transcription in the Heritage 2022 metadata does not match the file content. The label is the
only content description these 200 files have, so this is the collection's defining problem —
and the one the pipeline is best placed to measure, since a description generated from picture
and sound does not depend on the barcode at all. Section 2 of the analysis page covers this.

# Pipeline

Configured in `collections.json` (collection id `nwfa-400`). Separators are detected first,
the file is cut on them, and each clip is described on its own.

```
video file
  → extract_sound_ffmpeg → detect_speech_vad → transcribe_speech_parakeet (canary-1b-v2)
  → transcription_vad_sub → sub_clips_ffmpeg
  → answer_separators_vlm   (prompt: sep1,   max_fps 2)
  → separate_clips_ffmpeg
  → answer_clips_vlm        (prompt: misc3,  max_fps 1)
  → one row per proposed programme
```

Model for both VLM steps: `RedHatAI/Qwen3.8-27B-INT4`, seed 1234, `reasoning_effort xhigh`,
`video_tokens 64k`, `max_tokens 30k`. Hosted on CREATE — archive video never leaves KCL
infrastructure.

Sample filters are predefined in `collections.json`: `sample1`, `sample2`, `sample4`,
`sample10`, `sample15`, `sample20`, then `part1`–`part7` and `half1`/`half2` for the full run.

# Analysis page

`issa_ws2_nwfa.html` reads three JSON files sitting beside it. Chart.js, served via GitHub
Pages like the other pages.

| File | Contents |
|---|---|
| `nwfa_metadata_data.json` | catalogue aggregates for both batches, field completeness, the hierarchy bands |
| `issa_ws2_predictions.json` | pipeline aggregates for the current run: programmes per file, separators, coverage, non-content clips, field completeness, vocabularies, segments, duration cross-check, example timelines |
| `issa_ws2_humantruth.json` | the NWFA validation sample; a scaffold with the proposed field list until the sample returns |

The page carries a **stage** badge driven by `issa_ws2_predictions.json`:

- `first-pass` — fewer than 15 files processed (preparatory call 1)
- `validated` — 15 or more, human truth returned (preparatory call 2)
- `full` — 300 or more (the workshop)

Sections that have no data yet render a dashed "pending" block and fill themselves in when the
JSON gains the relevant keys. Nothing in the HTML needs touching between stages.

## Separators are derived, not read

The separator operator's own output was not available when the page was first built, so
separator positions are **derived by subtraction** in `make_ws2_data.py`: `separate_clips_ffmpeg`
excises separators, so every gap between consecutive clips is a detected separator and a
non-zero start on the first clip is a leading one. Exact for position and duration; it cannot
recover what the detector thought each separator was. Replace with the operator's output when
available, and drop the caveat in section 5.

## Model-written text

Section 2 cannot be made without short content gists for the sampled Channel M tapes, so
`issa_ws2_predictions.json` carries one gist per sampled file. Everything else in both JSON
files is aggregate counts. Pass `--no-gists` at full scale to drop them; the page detects this
and adjusts its provenance note automatically.

# Scripts

- `make_ws2_data.py`: generates all three JSON files from the two catalogue exports plus the
  current predictions file. Stage-agnostic — the same invocation works at 10, 15 and 400 files.

```bash
python make_ws2_data.py \
    --channelm    "data/input/NWFA/Channel M ISSA.xlsx" \
    --fvcat       "data/input/NWFA/ISSA FV Cat data.xlsx" \
    --predictions "data/output/ws2/predictions-10.v1.xlsx" \
    --humantruth  "data/input/NWFA/kdl_sample10_annotated.xlsx" \
    --out         workshops/ws2
```

Options: `--run v1` (default: parsed from the predictions filename), `--stage` to override the
badge, `--no-gists` to omit all model-written text. Accepts `.csv` or `.xlsx` predictions.

```bash
# view locally — the page fetches its JSON, so it needs a server
cd workshops/ws2 && python -m http.server 8000
# → http://localhost:8000/issa_ws2_nwfa.html
```

# Re-running at each stage

1. **After call 1** — refinements agreed with NWFA go into `collections.json` (prompt, the
   short-clip drop rule, the vocabulary targets). Re-run the pipeline on `sample15` or
   `sample20`.
2. **Before call 2** — NWFA returns the validation sample. Re-run `make_ws2_data.py` with
   `--humantruth` pointing at the completed spreadsheet; section 9 fills in and the stage badge
   moves to `validated`. Assign the `verdict` values in `label_match.items` once NWFA has
   confirmed them.
3. **Before the workshop** — full 400-file run, `--no-gists`, stage becomes `full`.

# Human-truth sample

Deliberately asymmetric, because the two batches hold opposite amounts of existing metadata and
human annotation time is the scarce resource:

| Field | Asked of | Why |
|---|---|---|
| `label_matches_content` | Channel M | The only field that addresses the barcode error. One verdict per tape. |
| `nb_progs` | both | No source holds this. The core outer-segmentation reference. |
| `prog_timecodes` | both | No source holds this. Scores boundary placement, not just counts. |
| `machine_text_verdict` | both | Accept / amend / reject on the machine summary, with a reason. |
| `year`, `colour`, `sound` | Channel M only | Already catalogued for all 200 Film & Video records. |

# TODO

- [ ] Replace derived separators with `answer_separators_vlm` output
- [ ] Apply the short-clip drop rule (clips under ~5s bounded by separators on both sides)
- [ ] Add a `non-content` value to the `types` vocabulary in the clip prompt
- [ ] Decide the programme unit for rushes (story vs take) before scale-up
- [ ] Re-point the prompt at NWFA's `category` / Professional–Amateur vocabularies
- [ ] Measure what the audio chain (VAD + transcription) contributes
- [ ] Settle the catalogue-runtime vs file-duration rule with NWFA
- [ ] Test whether the barcode error is systematic (offset or crate transposition)
- [ ] YFA strand of WS2
