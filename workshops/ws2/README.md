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
  → extract_sound_ffmpeg → detect_speech_vad → transcribe_vad_parakeet (canary-1b-v2)
  → transcription_vad_sub → sub_clips_ffmpeg
  → answer_separators_vlm   (prompt: sep1,        max_fps 2)
  → separate_clips_ffmpeg
  → answer_clips_vlm        (pass 1 · prompt: misc3,       max_fps 1)
  → answer_clips_vlm        (pass 2 · prompt: secondpass1, max_fps 1)
  → one row per proposed programme (13 fields)
```

The clip is described twice. Pass 1 (`misc3`) returns the descriptive fields — year, title,
places, segments, summary, synopsis, colour, NWFA's `category` / `category2` vocabularies,
keywords, credits. Pass 2 (`secondpass1`) returns a `programme` flag (is this clip real
programme content or just markers), the bands in it, and a two-word `environment`.

Model for both VLM steps: `RedHatAI/Qwen3.8-27B-INT4`, seed 1234, `reasoning_effort xhigh`,
`video_tokens 64k`, `max_tokens 30k`. Hosted on CREATE — archive video never leaves KCL
infrastructure.

Sample filters are predefined in `collections.json`: `sample1`–`sample20` (including
`sample1b`), `part1`–`part7` and `half1`/`half2` for the full run, plus `replay1`/`replay10`/
`replay30`.

# Analysis page

`issa_ws2_nwfa.html` reads three JSON files sitting beside it. Chart.js, served via GitHub
Pages like the other pages.

| File | Contents |
|---|---|
| `nwfa_metadata_data.json` | catalogue aggregates for both batches, field completeness, the hierarchy bands (the working-sample row collapses to the annotated dots above ~40 files) |
| `issa_ws2_predictions.json` | pipeline aggregates for the current run: programmes per file, separators, coverage, non-content clips (heuristic + the second-pass `programme` flag), field completeness, vocabularies and category agreement against the catalogue, segments, duration cross-check, example timelines |
| `issa_ws2_humantruth.json` | the 10-video validation sample as returned by five annotators: per-field answers, agreement on programme counts, boundary placement against the pipeline's proposed programmes, and the label-match verdicts (which also fill section 2) |

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
python3 workshops/ws2/make_ws2_data.py \
    --channelm    "data/output/NWFA_metadata/Channel M ISSA.xlsx" \
    --fvcat       "data/output/NWFA_metadata/ISSA FV Cat data.xlsx" \
    --predictions "data/output/NWFA_metadata/predictions-400.v4.xlsx" \
    --labelmatch  "data/output/NWFA_metadata/matched_labels_200.xlsx" \
    --annotations data/output/NWFA_metadata/NWFA_annotation_*.xlsx \
    --out         workshops/ws2 \
    --no-gists
```

Options: `--run v4` (default: parsed from the predictions filename), `--stage` to override the
badge, `--no-gists` to omit all model-written text, `--humantruth` for the flat sent-sample
sheet (pre-workshop scaffold, superseded by `--annotations`). `--labelmatch` takes the
label-pool search workbook (`matched_labels_200.xlsx`: each Channel M tape's machine
description embedded against the full H22 label list, top-5 candidates, `%match1` and
`simDif` per tape) and emits the `label_pool` block that drives section 2 — the
green/yellow/blank classes are reproduced from the sheet's own conditional-formatting
rules. Accepts `.csv` or `.xlsx` predictions; the `NWFA_annotation_*.xlsx` glob picks up
the untouched template workbook, which the script skips with a warning.

The current JSONs are generated with `--no-gists`: section 2 no longer displays
model-written content gists, so `contains_model_text` is `false` and the provenance note
in the footer reads "Aggregates only".

```bash
# view locally — the page fetches its JSON, so it needs a server
cd workshops/ws2 && python -m http.server 8000
# → http://localhost:8000/issa_ws2_nwfa.html
```

# Re-running at each stage

1. **After call 1** — refinements agreed with NWFA go into `collections.json` (prompt, the
   short-clip drop rule, the vocabulary targets). Re-run the pipeline on `sample15` or
   `sample20`.
2. **Before call 2** — NWFA returns the validation sample as per-annotator workbooks
   (`NWFA_annotation_<NAME>.xlsx`). Re-run `make_ws2_data.py` with `--annotations`; section 9
   fills in (agreement and boundary placement), and the label-match verdicts — the majority of
   the annotators' yes/partly/no answers per tape, `mixed` where there is no majority — appear
   in the verdict column of the section 2 table (joined onto the label-pool rows). The stage
   badge moves to `validated`.
3. **Before the workshop** — full 400-file run, plus `--labelmatch` for the label-pool search
   and `--no-gists`; stage becomes `full`.

# Human-truth sample

Deliberately asymmetric, because the two batches hold opposite amounts of existing metadata and
human annotation time is the scarce resource:

| Field | Asked of | Why |
|---|---|---|
| `label_match` (yes / partly / no) | Channel M | The only field that addresses the barcode error. One verdict per tape. |
| `nb_progs` | both | No source holds this. The core outer-segmentation reference. |
| `prog_timecodes` | both | No source holds this. Scores boundary placement, not just counts. |
| `year`, `colour`, `sound` | Channel M only | Already catalogued for all 200 Film & Video records. |
| `notes` | both | Anything odd — where the sample talks back. |

All ten videos were returned by five annotators. A programme row with a start time but no end
time is read as "to end of file".

# TODO

- [x] Re-point the prompt at NWFA's `category` / `category2` vocabularies — done in v4;
      section 7 measures the agreement (183 of 197 comparable films share ≥1 subject term;
      the provenance labels need a Special Interest ↔ Amateur/Home Movies alias)
- [ ] Non-content: the second pass's `programme` flag marks 46 of 590 programmes `false`;
      agree with NWFA on the drop mechanism — the flag, the duration rule (short clips bounded
      by separators on both sides), or both
- [ ] Replace derived separators with `answer_separators_vlm` output
- [ ] Decide the programme unit for rushes (story vs take) — the contested tape N_6966411
      (annotators count 13–14, pipeline proposes 11) keeps this live
- [ ] Measure what the audio chain (VAD + transcription) contributes
- [ ] Settle the catalogue-runtime vs file-duration rule with NWFA
- [ ] Test whether the barcode error is systematic (offset or crate transposition) — first
      data: 4 of the 5 label-verdicted tapes mismatch, the fifth contested
- [ ] YFA strand of WS2
