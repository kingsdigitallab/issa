# Prompt-informed evaluation notes

How the `sep1` and `misc2` prompts in `collections-batches.json`
(`meta.params.answer_separators_vlm.questions.sep1` and
`meta.params.answer_clips_vlm.questions.misc2`) reframe the conclusions in
`30-metadata-predictions-evaluations.md`. Mostly, they move several findings
from "model weakness" to "prompt design choice".

## The prompts, verbatim

**sep1** (tape → programme boundaries):

> List every full-screen separator between distinct programmes. A visual
> separator usually looks like SMPTE color bars, blank screen, production card,
> countdown leaders, static or white noise. It is always totally distinct in
> style from surrounding programmes, usually non-photographic and never
> intended for public audience. Compare with programmes on either side of the
> separator to confirm this. Return an empty list if the input doesn't contain
> any definite separator. Other screens within a programme like ending credits
> or chapter titles should not be reported as programme separators but may help
> finding/confirming nearby separators.

**misc2** (programme → metadata fields):

> The attached video is a single programme from a national archive. Returns a
> json dictionary with the following keys:
> * year (the year the programme was made, only if specified and certain),
> * place (shortlist of regions or specific identifiable place names where this is filmed),
> * title (the title of the programme, if specified),
> * segments (list of main chapters or major segments, for each a `title` and a `starting` timecode),
> * summary (one very concise sentence summarising the content of the programme),
> * synopsis (one longer sentence summary of the content of the programme),
> * colour (either: black-and-white or colour or sepia or colour-and-black-and-white),
> * fiction (yes if definitively fiction, no otherwise),
> * types (one or more values from tv news, amateur, educational, sponsored, advertising, animation, documentary, promotional, fiction, drama, tv sports, instructional, religion, comedy, horror, home movie, scientific),
> * keywords (10 key topical or thematic tags for this programme; avoid overly specific tags like place names, people or objects),
> * credits (if specified).

## What the misc2 prompt tells us

### Abstention is policy, not failure

The qualifiers "only if specified and certain" (year), "if specified"
(title, credits) mean the sparse coverage numbers are compliance, not
weakness:

- **year**: 11/70 predicted is the intended coverage/precision trade-off; the
  meaningful metric is precision-when-committed, which is high (9/11, and both
  misses are borderline: `85060728` predicted 1962 against a GT date range
  ending 1966; a "People of the Year 1995" item dated 1994).
- **title**: 56/61 empty titles on news tapes follow "if specified" — news
  items rarely state an on-screen title. The GT shotlist entries have
  *descriptive* titles ("Nail cutting for cows"); producing those would
  require the prompt to ask for a descriptive title.
- **credits**: sparse by the same clause.
- **fiction** ("yes if definitively fiction"): the 69/69 score carries a
  built-in conservative bias, but both GT fiction films (`Robot Three`,
  `Sisyphus`) were still caught — not "no" by default.

### The types taxonomy: designed for the full 400-film catalogue

The predictions were produced on a ~16-tape validation sample, but the full
batches contain 400 videos whose ground truth is `catalogue/metadata-400.ods`
(402 rows, 400 with DOD prefixes, same 27-column schema, no place column).
The prompt's type list was evidently designed against that full catalogue,
which revises the sample-based bucket analysis:

1. **Most sample-era "drift" labels are legitimate against the full GT**:
   `documentary` (20+ uses, plus concatenations), `promotional` (9+),
   `drama`, `comedy`, `home movie`, `religion`, `scientific`, `advertising`,
   `fiction`, `horror`, `animation`, `instructional`, `educational`,
   `sponsored`, `amateur` all appear in metadata-400. The doc-30
   "predicted but not in GT" counts are largely a sampling artifact of the
   16-film subset, so the mapped micro-F1 (0.421 A / 0.271 B) *understates*
   model quality against the full taxonomy.
2. **Genuinely absent from the prompt**: `local topical` (6 uses) plus niche
   labels (`medical`, `industrial`, `expedition`, `music`, `tv arts`,
   `sport`, `travelogue`, `cine mag`, `topical`).
3. **GT type-value data quality is the bigger problem**: the 400-row `type`
   column contains unseparated concatenations (`sponsoreddocumentary`,
   `tv newstv arts`, `amateurcomedy`), multi-word labels
   (`amateur documentary`), and stray punctuation (`educational;`,
   `educational; sponsored`). Full-scale evaluation needs separator-aware
   GT parsing (implemented in `eval_predictions_v2.py`, which now reads
   `.ods` GT via `--gt` and parses concatenated type values).
4. **What remains a genuine model miss**: `tv news` recall on news tapes —
   GT types news tapes `tv news` 195 times, but the model labelled most
   tape items `documentary`.

Because `promotional`/`advertising` and `home movie`/`amateur` are distinct
labels in the full GT, the evaluation's synonym map was reduced to the
spelling variant `tv sports → tv sport` (GT uses `tv sport`/`sport`).

### Field-level confirmations

- **colour**: the prompt enum (`black-and-white`/`colour`/`sepia`/
  `colour-and-black-and-white`) matches the evaluation's `COLOUR_MAP`
  normalization 1:1 — it wasn't a guess. Since the model answers per
  *programme*, B/W items judged against tape-level GT are a reference-level
  artifact, not errors.
- **segments**: the prompt asks for "main chapters or major segments"; GT
  shotlists are shot-level catalogue entries (`gvs`, `cu`, ALL CAPS) for
  class A films. The 7.4-vs-18 count gap and 0.12 matched-pair F1 are largely
  definitional — the shotlist comparison doesn't measure what the prompt
  requested. For B tapes the GT shotlist instead lists programmes, which
  makes the field double as a programme detector (see "The segments field's
  dual role" below).
- **summary/synopsis**: "one very concise sentence" / "one longer sentence"
  confirms the ROUGE-1 ≈ 0.23–0.25 is style-driven understatement of semantic
  quality, not content error.
- **place/keywords**: keywords explicitly exclude place names, and place has
  no GT column — both fields are designed for search/discovery, not catalogue
  parity. The "unassessable" verdict in doc 30 is reinforced.

### The false premise for separator fragments

The prompt asserts "The attached video is a single programme". For clips that
are actually separator/leader fragments this premise is false, so their
metadata (B/W colour bars, no title) is correct-for-content but noise for
catalogue scoring.

### Relative segment timecodes

The `starting` timecodes in predicted `segments` are **relative to the clip
offset encoded in `kdl_prog`** (e.g. `00.44.10-338` means the clip starts at
00:44:10 on the tape). `eval_predictions_v2.py` already accounts for this: the
`kdl_prog` start is added to predicted segment times before matching GT
shotlist timecodes (class A clips start at 00:00:00, so the offset is 0;
class B clips get lexical-only segment comparison because tape shotlists
have no sub-programme timecodes).

## What the sep1 prompt tells us

- **It defines the clip boundaries the class-B evaluation rests on.** The
  ≤5s clip-to-shotlist offsets validated the 30s matching tolerance, and the
  tape-head bars/black screens counted as separators explain why each tape's
  first clip starts ~5s before its first shotlist entry.
- **Only visual separators are detected** — news items separated by a plain
  cut get merged. Hence 27 clips vs 32 GT shotlist entries on `234552207`:
  per-programme comparison on tapes has a recall ceiling set by `sep1`, not
  `misc2`.
- **The 3 unmatched clips (`140179431 00.40.25-1`, `140180335 00.46.52-1`,
  `140833800 00.33.28-832`) look like separator/leader fragments promoted to
  "programmes"** (the `-1` suffix pattern also appears in the first clips of
  `144133880`). They inflate the colour-error count; expected tape colour
  accuracy rises from 56/61 once they are excluded.
- The 7 empty `sep1` answers on single-film tapes are correct abstentions —
  a pipeline sanity check that class A films are indeed single programmes.

## The segments field's dual role

The GT `shotlist` column means different things per class: shot/scene codes
for class A films, programme entries (often not visually separated) for
Grampian tapes. Between the programme level and the shot/scene level the GT
has no intermediate (chapter) level — which is exactly what the misc2
`segments` field captures. Consequences measured by the evaluation:

- **A (the missing mid-level)**: the model consistently produces 4–12
  chapters per film while GT shotlists range from 1 to 56 codes — the
  comparison is cross-level. Mean time-P is 0.52, and rises to 0.71–1.0 on
  films whose GT is genuinely shot-level (83972061: 1.0, 85060728: 0.909,
  91174079: 0.714); where the GT has almost no codes (103008963: 2,
  260522455: 1) the model's boundaries cannot be credited. The doc-30
  time-R of 0.34 was a cross-level artifact, not under-segmentation.
- **B (second-chance programme detection)**: 17 of 74 GT programme starts
  have no clip start within ±30s (separator absent, flashing, or missed by
  the model). Inner segments recover 15/17, raising programme-boundary
  coverage from 57/74 (77%) to 72/74 (97%). Only two programmes remain
  undetected (139329389: "Summerhill Academy, Aberdeen", "Hercules the bear
  at Bucksburn School."). Segment titles also echo the recovered
  programmes' titles — e.g. "Western Isles Hospital exterior…" for "EXT GVS
  WESTERN ISLES GENERAL HOSPITAL IN STORNOWAY", and "Adjacent Asda
  supermarket car park" for "EXT GVS ASDA SUPERSTORE AT BRIDGE OF DEE".
- **The dual use is ambiguous**: the same field encodes chapters within a
  programme (A films and single-programme B clips) and undetected programme
  boundaries (8/61 B clips whose segments span multiple GT programmes, e.g.
  140179431 `00.13.02-1604` spans 6). A downstream consumer cannot tell
  the two apart.

Design recommendation: split the semantics into two fields/questions —
`programmes` (boundaries of distinct programmes detected within the clip,
acting as the sep1 backup; the "single programme" premise should be amended
for clips that contain several) and `chapters` (mid-level segmentation of a
single programme). For A only `chapters` applies; for B both do.

## Net effect on the conclusions in doc 30

1. Several "weaknesses" — year coverage, empty tape titles, sparse credits,
   segment granularity, low text similarity — are **prompt design choices**
   to revisit, not model defects.
2. The **types evaluation is re-based on the full 400-film GT**: most
   sample-era vocabulary drift dissolves (`documentary`, `promotional`,
   `drama`… are legitimate labels), so the actionable gaps are `tv news`
   recall on news tapes, the prompt's missing `local topical`, and GT
   type-value data quality (concatenations), which the eval script now
   parses robustly.
3. **Colour misses on tapes should be re-scored** after excluding
   separator-fragment clips (56/61 → expected 56/56 of genuine programmes).
4. **The segments field should be split** into `programmes` (sep1 backup) and
   `chapters` (mid-level) — its dual use is confirmed valuable (97% programme
   coverage with segments vs 77% from clip starts alone) but ambiguous (see
   "The segments field's dual role"). Tape-item titles would also need prompt
   changes.

Follow-up done: `eval_predictions_v2.py` now reads xlsx or ods ground truth
(`--gt catalogue/metadata-400.ods` for the full run; verified to give
identical per-clip scores to the metadata-16 xlsx for the sample films),
parses concatenated GT type values, and scores the segments dual role
(second-chance programme recall, per-segment window-matched title recall,
multi-programme clip flags in `seg_second_chance` / `seg_prog_windows`).
Remaining follow-ups: record the prompt changes (types list incl.
`local topical`, descriptive titles for news items, `tv news` emphasis for
news tapes, and the `programmes`/`chapters` field split) for the next
inference round.
