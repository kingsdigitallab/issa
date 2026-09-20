# Improvement recommendations for method and prompts

Concrete recommendations to improve prediction quality in the next inference
round, grounded in the measured findings of
`30-metadata-predictions-evaluations.md` and
`31-prompt-informed-evaluation-notes.md`. Target: the `sep1` (tape → programme
separation) and `misc2` (programme → metadata) questions in
`collections-batches.json`.

Important constraint: the full collection is ~100k tapes from different
channels, sources and decades. Separator *kinds* are therefore an open set —
the prompt must define what a separator *is* and let the model recognise
unlisted kinds; only the descriptive `kind` label is free text. By contrast,
the `types` taxonomy in misc2 stays closed because it maps onto the
catalogue's controlled vocabulary.

## Method recommendations (pipeline, not prompt)

1. **Cut rule**: never create sub-clips *of* separator regions (the
   `-1`-suffix fragments), and set a minimum clip length (~10s) — removes
   the 3 unmatched fragments and most class-B colour "misses".
2. **Split multi-programme clips downstream**: use the new `programmes` field
   to cut clips that contain several programmes into one catalogue row per
   programme (8/61 clips are affected). This resolves the dual-use ambiguity
   without renaming `segments`.
3. **Post-normalise** type spelling (`tv sports→tv sport`) and colour values
   in the CSV builder (mappings already implemented in
   `catalogue/eval_predictions_v2.py`).
4. **Keep the JSON salvage** as defense-in-depth, and add a validation pass
   (all keys present, types from the closed set, timecodes well-formed) with
   one retry on invalid answers (1/70 answers needed salvage this round).
5. **Extend `prog_answers_to_csv.py` FIELDNAMES** for the new answer keys
   (`is_content`, `programmes`, `title_descriptive`) when the next round lands.
6. **Re-run the evaluation** after the next round (the script accepts the
   full-400 GT via `--gt catalogue/metadata-400.ods`). Success criteria:
   tape programme coverage 72/74 → ≥74/74 as a first-class extraction;
   `tv news` misses on tapes 44 → ≈0; class-B title coverage 56/61 empty →
   near-full via descriptive titles; types micro-F1 (B 0.271 / A 0.421) →
   substantially up; credits token P/R (A 0.65) → up.

## Revised sep1 prompt

```
You are analysing a digitised video from a national film archive. The tape may contain several distinct programmes.

List every full-screen VISUAL SEPARATOR between two distinct programmes. A separator is a brief interruption that is totally distinct in style from the programmes on either side, usually non-photographic, and never intended for the public audience. Typical examples include SMPTE colour bars, blank or black screens, countdown leaders, static or white noise, production or copyright slates, and station cards - but the collection spans many channels, sources and decades, so expect separator kinds not listed here: judge each candidate by the definition above, not by resemblance to the examples. The key test: the separator marks a change from one programme to a DIFFERENT programme (confirm by comparing the content on either side).

Rules:
- Report a leader at the very start of the tape (e.g. bars or black before the first programme) as a separator starting at 00:00:00.
- Do NOT report screens that belong to a single programme: end credits, chapter titles, intertitles, or idents inside a programme. They may help you locate or confirm a nearby separator.
- Do NOT report plain cuts, fades or dissolves between scenes, even between news items on a compilation tape. Missing such boundaries is expected; a later pass recovers them. Do not guess.
- Return an empty list if the video contains no definite separator.

Return ONLY a raw JSON array (no markdown fences, no commentary) of objects with keys "start" (HH:MM:SS), "end" (HH:MM:SS) and "kind" (a short free-text label for what the separator is, e.g. "bars", "black", "leader", "static", "slate"), timecodes relative to the start of this video.
```

## Revised misc2 prompt

```
The attached video is a clip from a digitised archive tape, cut automatically around a single programme. Occasionally the cut is imprecise: the clip may contain only a fragment (colour bars, leader, static), or more than one short programme. Analyse the actual content and answer accordingly.

Return ONLY a raw JSON dictionary with the following keys. No markdown fences, no commentary, double quotes, null (never None), [] for unknown lists, and every key present. All timecodes use MM:SS and are relative to the start of this clip:

* is_content (false if the clip shows no programme content, such as colour bars, countdown, static or black screen; in that case set every other value to null or [] and ignore the rest of this list),
* programmes (the boundaries of each distinct programme contained in this clip, each an object with "start" (MM:SS), "end" (MM:SS) and a one-line "description"; return [] if the clip is one continuous programme),
* title (the on-screen or announced programme title, null if there is none),
* title_descriptive (always provided: a 5-10 word factual descriptive title in archive shotlist style, e.g. "Rugby tournament for Aberdeen schoolchildren"),
* year (the year of making or broadcast if stated, announced, shown on screen, or clearly evidenced in the content; otherwise null - do not guess),
* place (shortlist of specific identifiable places or regions where this is filmed, most specific first),
* colour (either: black-and-white or colour or sepia or colour-and-black-and-white - of the footage in this clip),
* fiction (yes if definitively fiction, no otherwise),
* types (one to four values from the taxonomy below, most specific first),
* summary (one very concise sentence describing what the programme shows),
* synopsis (one to three factual sentences in archive-catalogue style: what is shown, where, who or what appears, what is said or written on screen; no subjective evaluation),
* segments (three to twelve major chapters of the programme - not shot-by-shot - each with a `title` of 5-10 factual words and a `starting` timecode in MM:SS, relative to the start of this clip),
* credits (a dictionary, only with on-screen or spoken evidence, with any of the keys: director, producer, presenter, writer, production_company, sponsor, other; null when unknown),
* keywords (10 key topical or thematic tags for this programme; avoid overly specific tags like place names, people or objects).

The types taxonomy (never invent labels outside it):
* tv news - news reports, current-affairs items, press events, or general views shot for a TV news broadcast; any clip from a TV news compilation MUST include "tv news";
* tv sport - sports coverage or sports news;
* documentary - a constructed non-fiction film with narration or an argument;
* amateur - made by a non-professional film-maker;
* home movie - private or family footage;
* sponsored - made with the support of an organisation to promote its interests;
* advertising - contains paid commercials;
* promotional - promotes an organisation, event or cause without being a paid commercial;
* educational, instructional, scientific, religion, animation, fiction, drama, comedy, horror, music;
* local topical - a film about a specific local event or place of topical interest.

Second-chance separation ("programmes"): most clips contain a single programme, and [] is the correct answer. Report several entries only when the clip clearly contains distinct programmes: a different story, a new caption or on-screen title, an abrupt change of subject, presenter or studio.
```

## What each change targets (measured evidence)

| Change | Fixes |
|---|---|
| `programmes` field | 17/74 programme starts missed by sep1 (15 later caught by segments); makes second-chance detection first-class and unambiguous |
| `is_content` | 3 separator-fragment clips polluting colour/title scores |
| `title_descriptive` | 56/61 empty titles on tapes ("if specified" abstention); GT shotlist has descriptive titles to compare against |
| `tv news` MUST-rule + closed taxonomy + `local topical` + 1–4 cap | types recall 0.32 on tapes (44 `tv news` misses) and precision (documentary×36 over-labelling); micro-F1 0.271 B / 0.421 A |
| catalogue-style synopsis wording | ROUGE-1 F1 0.23–0.25 (GT mentions places, on-screen titles, facts) |
| structured `credits` keys | credits token P/R 0.65 (A) — maps directly onto GT `director/film-maker`, `production co`, `sponsor` columns |
| explicit "raw JSON only, null not None" | the 1/70 fenced-string answer needing salvage |
| sep1 leader rule + explicit timecode schema + open-set `kind` | `-1` fragment clips; implicit output format; unlisted separator kinds across the 100k-tape collection |
| `segments` MM:SS-relative, 3–12, "not shot-by-shot" | cross-level ambiguity (the field *is* the mid-level; timecodes were already relative — now stated) |

## Design decisions

- **Year policy — abstention kept**, with the evidence basis widened from
  "specified and certain" to "stated, announced, shown on screen, or clearly
  evidenced". Rationale: precision-when-committed is high (9/11) and the
  catalogue already holds tape-level years; the alternative (always give a
  best estimate plus a `year_certain` flag) would raise coverage at the cost
  of precision and an extra field. Revisit if per-programme years prove
  valuable for search.
- **Field naming kept**: `segments` retains its name (chapters semantics, now
  explicitly mid-level) so the pipeline (`prog_answers_to_csv.py`,
  `eval_predictions_v2.py`) needs no renames; the new `programmes` field
  carries the boundary-detection role, which is what removes the dual-use
  ambiguity.
- **Open-set separators vs closed-set types**: separator *kinds* must stay
  free text (100k tapes, many channels/decades — a closed `kind` enum would
  create blind spots); the *definition* in the sep1 prompt is the test, and
  the examples are explicitly non-exhaustive. Types, by contrast, are a
  controlled catalogue vocabulary and remain a closed list.
