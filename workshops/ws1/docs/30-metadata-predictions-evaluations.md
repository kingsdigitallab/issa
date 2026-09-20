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
  micro P/R/F1 (types, with synonyms `promotional→advertising`, `tv sports→tv sport`,
  `home movie→amateur`), hand-rolled ROUGE-1 and difflib ratio (summary/synopsis/title),
  timecode matching ±30s (segments vs shotlist), token-set containment (credits).

## Per-column quality

| column | vs GT column | quality A (single films) | quality B (compilation tapes) |
|---|---|---|---|
| title | `title` / shotlist entry title | 6/9 exact (2 GT titles uncertain placeholders; `Gas` vs `(ANTI-GAS…)`) | 0/58 exact, 56 empty predictions |
| year | `dateOfReleaseYYYY` / tx date | 3/9 predicted, 2/3 correct | 8/61 predicted, 7/8 correct |
| colour | `colour` | 8/9 (missed sepia) | 56/61 (misses plausibly B/W items on colour tapes) |
| fiction | `Non-Fiction/ Fiction` | 8/8 (1 GT-blank skipped) | 61/61 |
| types | `type` | mapped micro-F1 0.50 | mapped micro-F1 0.28; `documentary`×36 unconfirmed, GT `tv news` missed ×44 |
| summary | `synopsis` | mean ROUGE-1 F1 0.25 | n/a (no per-programme GT) |
| synopsis | `synopsis` | mean ROUGE-1 F1 0.23 | n/a (no per-programme GT) |
| segments | `shotlist` timecodes | time-P 0.52, time-R 0.34 (7.4 vs 18 entries), pair-F1 0.12 | programme-title token recall 0.19; 58/61 clips matched |
| credits | credits+director+sponsor+prod co | token P/R 0.65/0.65 over 6/9 | 0.125 over 4/61 (mostly n/a) |
| place | — | no GT column → not assessable | no GT column → not assessable |
| keywords | — | no GT column → not assessable | no GT column → not assessable |

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

1. **Types vocabulary drift** (F1 0.50 A / 0.28 B): the model uses modern descriptive
   labels (`documentary`, `educational`) against the archive's controlled scheme
   (`sponsored`, `advertising`, `local topical`, `tv news`), and rarely labels news
   tapes as `tv news` (missed 44/61). Likely prompt-solvable by supplying the GT
   taxonomy.
2. **Segment granularity/wording**: under-segments vs shotlist (7.4 vs 18 entries;
   time-R 0.34) and describes scenes differently (pair-F1 0.12) — timings are
   half-right, descriptions don't match catalogue phrasing.
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
- Needs prompt/taxonomy work: types, segment granularity, tape-item titles.
- Unassessable: place, keywords (no ground truth).
- The per-clip CSV (`catalogue/predictions.v2.eval.csv`) supports drilling into any of
  these findings.
