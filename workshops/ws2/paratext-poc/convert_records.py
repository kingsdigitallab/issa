#!/usr/bin/env python3
"""Convert two real examples (one Grampian, one non-Grampian) from the ISSA
pipeline's predictions + NLS catalogue ground truth into paratext's
"reviewing metadata you already have" JSONL shape (see
../../ws1/notebooks/predictions_analysis.ipynb for how the predictions were
parsed, and docs/review-views.md in the paratext repo for the JSONL shape).

Usage (from this directory):
    uv run python convert_records.py > records.jsonl
    uv run paratext package records.jsonl -p issa-segments
    uv run paratext review

No model is called here — every field below comes from files already in the
repo (kdl-metadata-385.v2(predictions-385.csv, sample-11.csv, segments_true/).

`media.src` points at where `copy-videos.bash` (workshops/ws1/) would place
the actual video file. It doesn't need to exist for packaging or for the
review UI to open — a missing file just shows as "can't play" in the player,
with a link to the path, until the real video is copied there.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

WS1 = Path(__file__).resolve().parents[2] / "ws1"
PREDICTIONS_CSV = WS1 / "kdl-metadata-385.v2(predictions-385.csv"
SAMPLE_CSV = WS1 / "sample-11.csv"
SEGMENTS_TRUE = WS1 / "segments_true"

PROG_RE = re.compile(r"^(\d\d)\.(\d\d)\.(\d\d)-(\d+)$")
SEG_ITEM_RE = re.compile(r"(?:^|;\s*)(\d{2}):(\d{2})(?::(\d{2}))?:\s*([^;]*)")
HMS_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2})$")
MS_RE = re.compile(r"^(\d{2}):(\d{2})$")


def hms_to_s(hh: str, mm: str, ss: str) -> int:
    return int(hh) * 3600 + int(mm) * 60 + int(ss)


def parse_inner_segments(raw: str) -> list[tuple[int, str]]:
    """'00:00:00: Foo; 00:04:47: Bar' -> [(0, 'Foo'), (287, 'Bar')], same
    MM:SS/HH:MM:SS ambiguity as predictions_analysis.ipynb — both examples
    below use HH:MM:SS consistently, so no per-programme resolution needed."""
    out = []
    for h, m, s, text in SEG_ITEM_RE.findall(raw or ""):
        secs = hms_to_s(h, m, s) if s else int(h) * 60 + int(m)
        out.append((secs, text.strip().rstrip(".")))
    return out


def load_ground_truth_segments(dod: int) -> list[dict]:
    """segments_true/<dod>.32.json -> [{start, end, text}], seconds."""
    raw = json.loads((SEGMENTS_TRUE / f"{dod}.32.json").read_text())
    out = []
    for item in raw:
        for key in ("start", "end"):
            m = HMS_RE.match(item[key]) or MS_RE.match(item[key])
            if not m:
                raise ValueError(f"unparsed timecode {item[key]!r} for {dod}")
            item[f"_{key}_s"] = hms_to_s(*m.groups()) if len(m.groups()) == 3 else int(m[1]) * 60 + int(m[2])
        text = item.get("desc", "")
        if item.get("tag"):
            text = f"{text} ({item['tag']})" if text else item["tag"]
        out.append({"start": item["_start_s"], "end": item["_end_s"], "text": text})
    return out


def video_src(dod: int) -> str:
    # Matches copy-videos.bash's own destination layout (workshops/ws1/sample11/).
    return str(WS1 / "sample11" / f"{dod}.32" / f"{dod}.32.mp4")


def make_outer_track(name: str, items: list[dict], note: str | None = None) -> dict:
    track = {"name": name, "items": items}
    if note:
        track["note"] = note
    return track


def catalogue_fields(row: pd.Series) -> dict:
    return {
        "title": row["title"],
        "year": str(int(row["dateOfReleaseYYYY"])) if pd.notna(row["dateOfReleaseYYYY"]) else None,
        "colour": row["colour"],
        "types": [t.strip() for t in re.split(r"[\n,;]+", str(row["type"])) if t.strip()],
    }


def build_grampian_records(df: pd.DataFrame, sample: pd.DataFrame) -> list[dict]:
    dod = 139329389
    progs = df[df["dod"] == dod].sort_values("start").reset_index(drop=True)
    cat = sample[sample["DODfilenameprefix"] == dod].iloc[0]
    gt_segments = load_ground_truth_segments(dod)
    file_end = max(gt_segments[-1]["end"], int((progs["start"] + progs["dur"]).max()))

    # -- Sample 1: whole file, OUTER segmentation (predicted programmes vs NLS ground truth) --
    outer_items = [
        {
            "start": int(r.start), "end": int(r.start + r.dur),
            "text": f"Programme {i + 1}: {r.types if pd.notna(r.types) else '(no type predicted)'}",
        }
        for i, r in progs.iterrows()
    ]
    predicted_types = sorted({t.strip() for ts in progs["types"].dropna() for t in ts.split(";")})
    outer_record = {
        "id": f"{dod}-outer",
        "extraction": {
            "title": None,  # no single title — the pipeline split this tape into several programmes
            "year": None,
            "colour": progs["colour"].dropna().iloc[0] if progs["colour"].notna().any() else None,
            "types": predicted_types,
            "summary": f"Pipeline split this tape into {len(progs)} programmes (predicted); "
                       f"NLS's own shotlist has {len(gt_segments)} timed items. See the two "
                       f"tracks below for where they agree and disagree.",
        },
        "ground_truth": catalogue_fields(cat),
        "metadata": {
            "media": {
                "src": video_src(dod), "start": 0, "end": file_end,
                "label": "Whole tape (outer segmentation)",
                "tracks": [
                    make_outer_track("Predicted programmes (outer)", outer_items),
                    make_outer_track(
                        "NLS shotlist (ground truth, outer)", gt_segments,
                        note="hand-annotated from the archive shotlist, not a model output",
                    ),
                ],
            }
        },
    }

    # -- Sample 2: zoom on programme 1, INNER segmentation (predicted segments within it) --
    prog1 = progs.iloc[0]
    inner_items = [
        {"start": int(prog1.start) + t, "text": text}
        for t, text in parse_inner_segments(prog1["segments"])
    ]
    inner_record = {
        "id": f"{dod}-prog1-inner",
        "extraction": {
            "title": None,
            "year": None,
            "colour": prog1["colour"] if pd.notna(prog1["colour"]) else None,
            "types": [t.strip() for t in str(prog1["types"]).split(";")] if pd.notna(prog1["types"]) else [],
            "summary": prog1["summary"],
        },
        # NLS has no programme-level record to compare against — only the
        # tape-level one, repeated here to make that gap visible rather than
        # leaving the panel blank.
        "ground_truth": catalogue_fields(cat),
        "metadata": {
            "media": {
                "src": video_src(dod), "start": int(prog1.start), "end": int(prog1.start + prog1.dur),
                "label": "Programme 1 (inner segmentation)",
                "tracks": [make_outer_track("Predicted segments (inner)", inner_items)],
            }
        },
    }
    return [outer_record, inner_record]


def build_non_grampian_record(df: pd.DataFrame, sample: pd.DataFrame) -> dict:
    dod = 75247299
    row = df[df["dod"] == dod].iloc[0]
    cat = sample[sample["DODfilenameprefix"] == dod].iloc[0]
    gt_segments = load_ground_truth_segments(dod)
    start, dur = int(row["start"]), int(row["dur"])
    inner_items = [{"start": start + t, "text": text} for t, text in parse_inner_segments(row["segments"])]
    predicted_types = [t.strip() for t in str(row["types"]).split(";")] if pd.notna(row["types"]) else []
    return {
        "id": f"{dod}-file",
        "extraction": {
            "title": row["title"], "year": None,
            "colour": row["colour"] if pd.notna(row["colour"]) else None,
            "types": predicted_types, "summary": row["summary"],
        },
        "ground_truth": catalogue_fields(cat),
        "metadata": {
            "media": {
                "src": video_src(dod), "start": 0, "end": max(start + dur, gt_segments[-1]["end"]),
                "label": "Whole file — single programme (outer + inner in one clip)",
                "tracks": [
                    make_outer_track(
                        "Predicted programme (outer)",
                        [{"start": start, "end": start + dur, "text": f"Programme 1: {', '.join(predicted_types) or '(no type predicted)'}"}],
                    ),
                    make_outer_track(
                        "NLS catalogue (ground truth, outer)", gt_segments,
                        note="catalogue treats this as one programme, matching the prediction",
                    ),
                    make_outer_track("Predicted segments (inner)", inner_items),
                ],
            }
        },
    }


def main() -> None:
    df = pd.read_csv(PREDICTIONS_CSV, encoding="cp1252")
    df.columns = ["batch", "dod", "prog", "title", "year", "place", "colour", "types",
                  "fiction", "summary", "synopsis", "segments", "credits", "keywords"]
    p = df["prog"].str.extract(PROG_RE).astype(int)
    df["start"], df["dur"] = p[0] * 3600 + p[1] * 60 + p[2], p[3]
    sample = pd.read_csv(SAMPLE_CSV)

    records = build_grampian_records(df, sample) + [build_non_grampian_record(df, sample)]

    print(json.dumps({"_provenance": {"project": "issa-segments", "model": "FrameSense + Qwen3.8-27B"}}))
    for r in records:
        print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
