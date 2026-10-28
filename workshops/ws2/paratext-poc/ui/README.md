# Patched review UI

`static/` is a copy of `paratext/review/static/` (from the pinned `video-review` branch).
Paratext's `app.js` is an ES module, so it cannot be extended from outside; `../serve_ws2.py`
points the review server at this copy instead. Only `app.js` and `index.html` differ from upstream —
the diff is the list below, so it can be rebased or offered upstream.

Stock datasets still render as before: the new layout switches on only for samples whose
`model_output.compare` and `media` are present.

| Change | Where |
|---|---|
| Track name above its strip (small), tracks stack closer | `mediaHtml`, `.media-track*` |
| Track groups from a name prefix: `pipe:` / `human:` / `ann:`. Only pipeline tracks stay in view; all human tracks (consensus + per annotator) fold into "Human annotation (N tracks)" | `trackInfo`, `mediaHtml` |
| Collection bar (`← Previous · collection · file · duration · Next →`) under the video and at the bottom | `collectionBar` |
| Item text prefixes `@sep`, `@agreed`, `@contested` styled (separators hatched; consensus solid, contested dashed border, no hatching) | `itemKind`, `bindTimeline`, `.kind-*` |
| Segments without an `end` run to the next segment's start; the item under the playhead is highlighted on tracks and in outlines | `bindTimeline` |
| Clip-window highlight hidden when it covers the whole file (it looked like a stray colour bar) | `bindTimeline` |
| Mirrored existing-vs-predicted grid with match status | `compareHtml` (reads `model_output.compare` / `.extras`) |
| Programme outlines (one line each, expandable to segments, ▶ seeks, expand/collapse all), placed between the tracks and the metadata grid | `outlineHtml`, `compareBody`, delegated click handler |
| Free-text rows (status `text`: synopsis, category, keywords) carry no ✓ ≈ ≠ marker; words present on both sides are highlighted instead (4+ letters or numbers, stop words ignored, plural `s` stripped) | `STATUS`, `factWords`, `overlapHtml`, `.cmp-val mark` |
| Annotator notes beside the verdict buttons | `scoreRowHtml` |
| `#media-error[hidden]` really hidden (Oat's alert style overrode it) | `index.html` |

Colour code (CSS variables in `index.html`): teal = existing record / human annotation,
purple = pipeline, blue = Film & Video, amber = Channel M.

Data contract these changes read is produced by `../convert_ws2.py`.
