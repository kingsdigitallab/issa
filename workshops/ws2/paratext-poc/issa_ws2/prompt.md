This is a review-only project — no model run is configured, so this prompt is
never sent anywhere. It exists so the schema/prompt/view audit passes.

Records are converted from the ISSA pipeline's existing output
(predictions-10.v3.xlsx) by ../convert_ws2.py and packaged directly.

Fields, for reference:

- `title`: the title, or for Channel M the label written on the tape.
- `year`: production year(s).
- `colour`: colour or black-and-white.
- `sound`: sound or silent.
- `duration`: running time.
- `types`: category labels.
- `programmes`: one line per programme with its start, length and summary.
- `label_matches`: the closest existing labels to each programme summary.
- `annotator_notes`: one line per human annotator.
- `compare`, `extras`, `outline`: the rows, extra fields and programme outline shown in the review UI.
- `agreement`, `collection`, `filename`, `file_duration`: context shown beside the video.
