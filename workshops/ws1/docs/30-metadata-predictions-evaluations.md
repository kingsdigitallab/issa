# Metadata predictions evaluations

Evaluation of `catalogue/predictions.v2.csv` (70 clips, 15 films) against the
ground truth in `catalogue/metadata-16.xlsx` (sheet `films-files`, 16 films),
produced by `catalogue/eval_predictions_v2.py`; per-clip scores in
`catalogue/predictions.v2.eval.csv`.

## Method

- Join on `DODfilenameprefix`. GT film `231298910` has no predictions (excluded).
- **Class A — single films** (9 clips, one per film): clip ≈ film, fields compared directly.
- **Class B — compilation tapes** (61 clips on 6 Grampian TV news tapes): tape-level
  GT fields (colour, fiction, types, year) compared per clip; each clip is matched to
  the nearest GT shotlist programme entry by `kdl_prog` start time (≤30s tolerance;
  58/61 matched, max distance 5s), enabling per-programme title/segments comparison.
- Metrics: normalized exact match (title, year, colour, fiction), mapped multi-label
  micro P/R/F1 (types, with the spelling synonym `tv sports→tv sport`; against the
  full 400-film GT, `promotional`/`advertising` and `home movie`/`amateur` are distinct
  labels and are not merged), hand-rolled ROUGE-1 and difflib ratio
  (summary/synopsis/title), timecode matching ±30s (segments vs shotlist), token-set
  containment (credits). Predicted segment `starting` timecodes are clip-relative and
  are offset by the clip's `kdl_prog` start before matching shotlist timecodes.
- The GT `shotlist` column is shot/scene-level for class A films but lists
  programmes for class B tapes. For B, each segment is additionally matched to
  the GT programme window containing it, and GT programme starts not covered
  by any clip start are checked against segment times ("second-chance"
  programme detection); multi-programme clips are flagged.

## Per-column quality

| column | vs GT column | quality A (single films) | quality B (compilation tapes) |
|---|---|---|---|
| title | `title` / shotlist entry title | 6/9 exact (2 GT titles uncertain placeholders; `Gas` vs `(ANTI-GAS…)`) | 0/58 exact, 56 empty predictions |
| year | `dateOfReleaseYYYY` / tx date | 3/9 predicted, 2/3 correct | 8/61 predicted, 7/8 correct |
| colour | `colour` | 8/9 (missed sepia) | 56/61 (misses plausibly B/W items on colour tapes) |
| fiction | `Non-Fiction/ Fiction` | 8/8 (1 GT-blank skipped) | 61/61 |
| types | `type` | mapped micro-F1 0.421 | mapped micro-F1 0.271; `documentary`×36 unconfirmed, GT `tv news` missed ×44 |
| summary | `synopsis` | mean ROUGE-1 F1 0.25 | n/a (no per-programme GT) |
| synopsis | `synopsis` | mean ROUGE-1 F1 0.23 | n/a (no per-programme GT) |
| segments | `shotlist` timecodes (A: shots/scenes; B: programme entries) | chapters vs shot-level GT, cross-level: time-P 0.52 (boundaries real), pair-F1 0.12 | second chance: segments recover 15/17 programmes missed by clip starts (57/74 → 72/74, 77% → 97%); per-segment title recall 0.06; 8/61 clips span multiple programmes |
| credits | credits+director+sponsor+prod co | token P/R 0.65/0.65 over 6/9 | 0.125 over 4/61 (mostly n/a) |
| place | — | no GT column → not assessable | no GT column → not assessable |
| keywords | — | no GT column → not assessable | no GT column → not assessable |

Note: the 16 tapes are a validation sample; the full batches contain 400 videos
with ground truth in `catalogue/metadata-400.ods`. The types vocabulary
comparison is re-based against that full GT in `31-prompt-informed-evaluation-notes.md`
— several "drift" labels (`documentary`, `promotional`, `drama`, …) are legitimate
against the full taxonomy. The eval script accepts any xlsx/ods GT via `--gt`.

Note: the GT `shotlist` column means different things per class — shot/scene
codes for class A films, programme entries for class B tapes — and there is no
ground-truth mid-level (chapter) segmentation. The predicted `segments` field
is evaluated accordingly: cross-level for A (time-P is the primary metric),
and as a second-chance programme detector for B (see doc 31).

## Overall conclusions

### What the model does well

- **Fiction/non-fiction**: essentially solved (69/69 scored clips correct) — a reliable, high-confidence field.
- **Colour**: strong (64/70); on tapes, the 5 "misses" are plausibly genuine B/W items
  judged against a tape-level reference, so real accuracy is likely higher.
- **Year when committed**: 9/11 correct — but the model abstains on ~84% of clips, so
  coverage, not accuracy, is the bottleneck.
- **Titles on single films**: 6/9 exact, and all 3 misses are soft (two GT titles are
  uncertain bracketed placeholders; `Gas` is a recognizable match) — effectively ~6/7
  on definite titles.

### Main weaknesses

1. **Types vocabulary drift** (mapped micro-F1 0.421 A / 0.271 B): the model
   uses descriptive labels (`documentary`, `educational`) where the 16-film
   GT uses a controlled scheme, and rarely labels news tapes as `tv news`
   (missed 44/61). See doc 31 for the re-based view against the full 400-film
   GT: most of these labels are legitimate there, so the actionable gaps are
   `tv news` recall on tapes and the prompt's missing `local topical` label.
2. **Segments are the missing mid-level — and a second chance**: for A films
   the model produces consistent chapter-level segmentation (4–12 per film)
   against GT shotlists of inconsistent granularity (1–56 codes); half its
   boundaries coincide with real GT codes (time-P 0.52, rising to 0.71–1.0
   where the GT is genuinely shot-level). The earlier time-R 0.34 was a
   cross-level artifact, not under-segmentation. On B tapes, segments
   recover 15/17 programmes missed by the separator pipeline, raising
   programme-boundary coverage from 57/74 (77%) to 72/74 (97%); 8/61 clips
   span multiple programmes. Descriptions still don't match catalogue
   phrasing (pair-F1 0.12, per-segment title recall 0.06).
3. **News-tape titles**: 56/61 empty — the model won't title individual news items;
   if needed, the prompt should require it.
4. **Free-text similarity**: summary/synopsis ROUGE-1 F1 ≈ 0.23–0.25 — but this partly
   reflects terse 1–2 sentence GT synopses vs detailed model prose; lexical scores
   likely understate semantic quality.

### Structural limits of the comparison

- No GT for `place` and `keywords` at all; no per-programme text for tapes;
  compilations can only be compared on tape-level fields plus timecode-matched titles.
- Small sample (9 single films); GT itself uncertain in places (bracketed titles,
  year ranges, one blank fiction); film `231298910` and 3/61 tape clips unmatched.

### Bottom line

- Reliably extractable now: fiction, colour, year-if-given, single-film titles.
- Needs prompt/taxonomy work: types, splitting the segments field's dual use
  (programmes vs chapters, see doc 31), tape-item titles.
- Unassessable: place, keywords (no ground truth).
- Prompt and method recommendations for the next inference round: see
  `32-improvement-recommendations.md`.
- The per-clip CSV (`catalogue/predictions.v2.eval.csv`) supports drilling into any of
  these findings.
