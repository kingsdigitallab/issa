# Paratext PoC — inspection & correction interface

A proof of concept for using [Paratext](https://github.com/nls-lst/paratext)
(`video-review` branch — not yet released to PyPI) as the review/correction
interface for ISSA's outer + inner segmentation, the way Mike Saunders (NLS)
showed for the card-index and video-review work at WS1.

**Branch, not main.** This lives on `feat--ws2-paratext-poc` until it's had a
look from Geoffroy (and ideally Mike, once we can see his actual NLS
deployment — `paratext-nls` / `mikegsaunders/paratext-space` are both
private). Nothing here has been merged.

## What it demonstrates

`convert_records.py` builds 3 real records — no fabricated data — from files
already in this repo:

- **`139329389-outer`** — a Grampian tape, whole-file view. Two tracks:
  our pipeline's predicted programme boundaries (3) against NLS's
  hand-annotated ground truth (`workshops/ws1/segments_true/`, 6 items).
  This is the real, current disagreement between the two, not a
  hypothetical one.
- **`139329389-prog1-inner`** — zoomed into predicted programme 1, showing
  the model's *inner* segmentation (from
  `workshops/ws1/kdl-metadata-385.v2(predictions-385.csv`). NLS has no
  programme-level record to compare against here — only the tape-level one,
  shown anyway so that gap is visible rather than the panel being blank.
- **`75247299-file`** — a non-Grampian film where predicted and catalogue
  agree on "one programme," with the model's inner segments shown alongside.

Schema/view: `issa_segments/` — a "NLS catalogue record" panel next to a
"Pipeline output" panel (title/year/colour/types/summary), per
[review-views.md](https://github.com/nls-lst/paratext/blob/video-review/docs/review-views.md)'s
compare-against-an-existing-record recipe.

## Known limitation of this PoC

**No actual video bytes.** `media.src` points at where
`workshops/ws1/copy-videos.bash` would put these two files
(`sample11/<id>.32/<id>.32.mp4`) — the environment this was built in has no
RDS mount, so the files aren't there. The review UI degrades exactly as
documented: the player shows "couldn't be played, open it directly" instead
of erroring, and the metadata panels work normally. **The track strips
(the actual timeline visualisation) don't render without a loadable video**
— they need the video element's duration to draw against. Run
`copy-videos.bash` for `139329389` and `75247299` first (or point `video_src()`
in `convert_records.py` at wherever you've already got them), then
`paratext review` again, to see the tracks for real.

## Running it

```bash
cd workshops/ws2/paratext-poc
uv sync
uv run python convert_records.py > records.jsonl    # needs pandas — uses the system
                                                      # python's pandas via a plain
                                                      # `python3 convert_records.py`
                                                      # if uv's isolated venv doesn't have it
uv run paratext package records.jsonl -p issa-segments
uv run paratext review --no-open   # binds 127.0.0.1 only — see "Privacy" below
```

Then open `http://127.0.0.1:5050` (facilitator's own machine, projected —
this is deliberately Option C from the workshop discussion, not something
attendees' own devices join).

## Privacy / video-serving (see the WS2 planning discussion)

Paratext's review server has **no login of its own** — access control is
entirely the network perimeter, by design. `--host` defaults to `127.0.0.1`;
that default is exactly what keeps this private for now. Do not pass
`--host 0.0.0.0` or otherwise put this on a shared network until a real
decision is made about how WS4/5 (individual attendee devices) will work —
see the conversation this PoC came out of for the options considered
(air-gapped room LAN, a private mesh VPN, vs. a KCL network segment).

## Next steps

- Real video files for these two IDs (or more), via `copy-videos.bash`.
- Compare against Mike's actual NLS project/view once he can share it —
  don't assume this PoC's field choices or track design match his.
- If this graduates past PoC: depend on `paratext-cli` normally (pin a
  released version once `video-review` merges) rather than the git-branch
  pin in `pyproject.toml`, which is temporary.
