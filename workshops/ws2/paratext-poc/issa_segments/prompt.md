This is a review-only PoC — no model run is configured, so this prompt is
never sent anywhere. It exists so the schema/prompt/view audit test passes,
and as a placeholder for if this project ever runs a live extraction (e.g.
NLS-style, attendees iterating on a prompt at a workshop).

The records reviewed here were produced by the ISSA FrameSense + Qwen3.8-27B
pipeline (see workshops/ws1/notebooks/predictions_analysis.ipynb), not by
this prompt, and packaged via `paratext package records.jsonl -p issa-segments`.

Fields, for reference:

- `title`: the programme's title, if any.
- `year`: release/production year.
- `colour`: colour / black-and-white / colour-and-black-and-white.
- `types`: one or more genre/type labels.
- `summary`: a one or two sentence summary.
