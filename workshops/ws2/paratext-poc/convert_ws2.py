#!/usr/bin/env python3
"""Convert the WS2 NWFA sample into paratext review records (one per video).

Inputs, all already in the repo / handed over by NWFA — nothing is generated:
  - predictions-10.v3.xlsx          pipeline output (programmes + inner segments)
  - NWFA_annotation_TEMPLATE_v0.1   catalogue facts for the 10 videos (Videos sheet)
  - NWFA_annotation_<NAME>.xlsx     zero or more completed annotator copies
  - semantic-matched-labels-10.docx Geoffroy's label matching (optional; partial)
  - *.pocket.mp4                    compressed videos, matched by reference

Usage (system python3 — needs pandas + openpyxl, which uv's venv doesn't have):
    python3 convert_ws2.py > records_ws2.jsonl
    uv run paratext package records_ws2.jsonl -p issa-ws2
    uv run paratext review --no-open

Annotators are picked up automatically: drop NWFA_annotation_<NAME>.xlsx files
into data/output/NWFA_metadata/ (or pass --annotations) and re-run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import html
import json
import re
import subprocess
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
META = ROOT / "data/output/NWFA_metadata"
FV_CAT = META / "ISSA FV Cat data.xlsx"
VIDEOS = ROOT / "data/output/NWFA_videos_sample"
LABELS_DOCX = ROOT / "data/output/semantic-matched-labels-10.docx"

TOL = 10  # seconds: boundaries this close count as the same boundary
COLLECTION = {"H22": "NWFA ― Channel M", "FV": "NWFA ― Film & Video"}

PROG_RE = re.compile(r"^(\d\d)\.(\d\d)\.(\d\d)-(\d+)$")
SEG_ITEM_RE = re.compile(r"(?:^|;\s*)(\d{1,2}):(\d{2})(?::(\d{2}))?:\s*([^;]*)")
SEG_LINE_RE = re.compile(r"^\s*(\d{1,2}:\d{2}(?::\d{2})?)\s+(.*)$")
REF_RE = re.compile(r"^(NWFA \d+|N_\d+)")


def fmt(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def parse_timecode(v) -> int | None:
    """HH:MM:SS or MM:SS as str, an Excel time/timedelta, or a day-fraction float."""
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
        return None
    if isinstance(v, dt.datetime):
        v = v.time()
    if isinstance(v, dt.time):
        return v.hour * 3600 + v.minute * 60 + v.second
    if isinstance(v, (dt.timedelta, pd.Timedelta)):
        return int(v.total_seconds())
    if isinstance(v, float):
        return int(round(v * 86400))
    parts = [int(p) for p in str(v).strip().split(":")]
    if len(parts) == 2:
        parts = [0, *parts]
    if len(parts) != 3:
        raise ValueError(f"unparsed timecode {v!r}")
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def ref_of(name: str) -> str:
    m = REF_RE.match(str(name))
    if not m:
        raise ValueError(f"no NWFA reference in {name!r}")
    return m[1]


# -- pipeline output ---------------------------------------------------------

def parse_inner_segments(raw: str) -> list[tuple[int, str]]:
    """'00:00: A; 04:24: B' -> [(0, 'A'), (264, 'B')]. Two components are MM:SS,
    three are HH:MM:SS — both occur in the same file. Relative to the programme."""
    out = []
    for a, b, c, text in SEG_ITEM_RE.findall(raw or ""):
        secs = int(a) * 3600 + int(b) * 60 + int(c) if c else int(a) * 60 + int(b)
        out.append((secs, text.strip().rstrip(".")))
    return out


def load_predictions(path: Path) -> dict[str, list[dict]]:
    df = pd.read_excel(path)
    by_ref: dict[str, list[dict]] = {}
    for r in df.itertuples():
        m = PROG_RE.match(str(r.kdl_prog))
        if not m:
            raise ValueError(f"unparsed kdl_prog {r.kdl_prog!r}")
        h, mi, s, dur = map(int, m.groups())
        start = h * 3600 + mi * 60 + s
        by_ref.setdefault(ref_of(r.DODfilenameprefix), []).append({
            "kdl_prog": r.kdl_prog, "start": start, "end": start + dur,
            "title": None if pd.isna(r.title) else str(r.title),
            "year": None if pd.isna(r.year) else str(int(r.year)) if isinstance(r.year, float) else str(r.year),
            "colour": None if pd.isna(r.colour) else str(r.colour),
            "types": [str(c) for c in (r.category, r.category2) if pd.notna(c)],
            "summary": "" if pd.isna(r.summary) else str(r.summary),
            "synopsis": _clean(r.synopsis), "places": _clean(r.places), "credits": _clean(r.credits),
            "keywords": _clean(r.keywords), "fiction": _clean(r.fiction),
            "category": _clean(r.category), "category2": _clean(r.category2),
            "segments": [(start + t, text) for t, text in parse_inner_segments(r.segments)],
        })
    return by_ref


# -- catalogue facts + annotators -------------------------------------------

def _clean(v) -> str | None:
    return None if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "" else str(v).strip()


def load_catalogue(template: Path) -> dict[str, dict]:
    v = pd.read_excel(template, sheet_name="Videos", header=2).iloc[:10]
    return {str(r["reference"]): {
        "batch": r["batch"], "label": _clean(r["label written on the tape"]),
        "title": _clean(r["title"]), "year": _clean(r["year"]), "colour": _clean(r["colour"]),
        "sound": _clean(r["sound"]), "catalogue_duration": _clean(r["catalogue duration"]),
    } for _, r in v.iterrows()}


def load_fv_catalogue(path: Path) -> dict[str, dict]:
    """Film & Video catalogue fields the pipeline also targets, keyed by reference."""
    if not path.exists():
        return {}
    df = pd.read_excel(path)
    out = {}
    for _, r in df.iterrows():
        if _clean(r.get("Filename")):
            out[ref_of(r["Filename"])] = {
                "category": _clean(r.get("category")), "place": _clean(r.get("ContentCounty")),
                "synopsis": _clean(r.get("synopsis")), "keywords": _clean(r.get("index_terms")),
            }
    return out


def load_annotator(path: Path) -> dict:
    """One completed NWFA_annotation_<NAME>.xlsx -> per-reference programmes,
    segments and the Videos-sheet answers."""
    head = pd.read_excel(path, sheet_name="Videos", header=None, nrows=1)
    # name box is the merged cell C1:E1
    name = _clean(head.iloc[0, 2]) or path.stem.removeprefix("NWFA_annotation_")
    videos = pd.read_excel(path, sheet_name="Videos", header=2).iloc[:10]
    answers = {str(r["reference"]): {
        "n_programmes": _clean(r["HOW MANY PROGRAMMES?"]),
        "label_matches": _clean(r["does the label match the content?"]),
        "notes": _clean(r["notes / anything odd"]),
    } for _, r in videos.iterrows()}
    progs: dict[str, list[dict]] = {}
    sheet = pd.read_excel(path, sheet_name="Programmes", header=2)
    for _, r in sheet.iterrows():
        ref = _clean(r["reference"])
        start, end = parse_timecode(r["starts (HH:MM:SS)"]), parse_timecode(r["ends (HH:MM:SS)"])
        if not ref or start is None:
            continue  # spare rows
        segs = []
        for line in (_clean(r.iloc[6]) or "").splitlines():
            m = SEG_LINE_RE.match(line)
            if m:
                segs.append((parse_timecode(m[1]), m[2].strip()))
        progs.setdefault(ref, []).append({
            "no": _clean(r["programme no."]), "start": start, "end": end,
            "text": _clean(r["what is it? (one line)"]) or "", "segments": segs,
        })
    return {"name": name, "answers": answers, "programmes": progs}


# -- Geoffroy's label matching (Word document, per programme) ------------------

def load_label_matches(path: Path) -> dict[tuple[str, str], dict]:
    """(reference, kdl_prog) -> {true, ranked: [(pct, label, is_true)]}."""
    if not path.exists():
        return {}
    xml = zipfile.ZipFile(path).read("word/document2.xml").decode()
    paras = [html.unescape(re.sub(r"<[^>]+>", "", p)) for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)]
    out, cur = {}, None
    for p in (p.strip() for p in paras):
        if p.startswith("prog:"):
            m = re.match(r"prog: batches/(N_\d+)_[^/]*/(\d\d\.\d\d\.\d\d-\d+)-", p)
            cur = out.setdefault((m[1], m[2]), {"true": None, "ranked": []}) if m else None
        elif cur is not None and p.startswith("true:"):
            cur["true"] = p[5:].strip(" []")
        elif cur is not None:
            m = re.match(r"(TRUE )?\d+\.\s+([\d.]+)% similar to '(.*)' \(misattributed", p)
            if m:
                cur["ranked"].append((float(m[2]), m[3], bool(m[1])))
    return out


# -- video -------------------------------------------------------------------

def find_video(videos: Path, ref: str) -> Path | None:
    hits = sorted(p for p in videos.glob("*.mp4") if p.name.startswith(ref + " ") or p.name.startswith(ref + "_"))
    return hits[0] if hits else None


def video_duration(path: Path) -> float | None:
    try:
        return float(subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]))
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None


# -- consensus between annotators --------------------------------------------

def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def cluster_programmes(annotators: list[dict], ref: str, tol: int = TOL) -> list[dict]:
    """Programmes two annotators 'agree' on have both boundaries within `tol` s.
    Returns [{start, end, text, support, n, members}] ordered by start."""
    n = len(annotators)
    clusters: list[dict] = []
    for ai, a in enumerate(annotators):
        for p in a["programmes"].get(ref, []):
            if p["end"] is None:
                continue
            for c in clusters:
                if (ai not in c["by"] and abs(p["start"] - _median(c["s"])) <= tol
                        and abs(p["end"] - _median(c["e"])) <= tol):
                    break
            else:
                c = {"s": [], "e": [], "by": {}, "segs": []}
                clusters.append(c)
            c["s"].append(p["start"]); c["e"].append(p["end"]); c["by"][ai] = p
    out = []
    for c in sorted(clusters, key=lambda c: _median(c["s"])):
        first = c["by"][min(c["by"])]
        out.append({"start": _median(c["s"]), "end": _median(c["e"]), "text": first["text"],
                    "support": len(c["by"]), "n": n, "members": list(c["by"].values())})
    return out


def cluster_segments(annotators: list[dict], ref: str, tol: int = TOL) -> list[dict]:
    n = len(annotators)
    clusters: list[dict] = []
    for ai, a in enumerate(annotators):
        for p in a["programmes"].get(ref, []):
            for t, text in p["segments"]:
                for c in clusters:
                    if ai not in c["by"] and abs(t - _median(c["t"])) <= tol:
                        break
                else:
                    c = {"t": [], "by": {}}
                    clusters.append(c)
                c["t"].append(t); c["by"][ai] = text
    return [{"start": _median(c["t"]), "text": c["by"][min(c["by"])], "support": len(c["by"]), "n": n}
            for c in sorted(clusters, key=lambda c: _median(c["t"]))]


def kind_of(support: int, n: int) -> str:
    """'' with a single annotator (no consensus to speak of)."""
    return "" if n < 2 else "agreed" if support == n else "contested"


def tag(kind: str, text: str) -> str:
    return f"@{kind} {text}" if kind else text


def human_outline(progs: list[dict], segs: list[dict]) -> list[dict]:
    out = []
    for i, p in enumerate(progs, 1):
        inside = [s for s in segs if p["start"] <= s["start"] < p["end"]]
        out.append({"start": p["start"], "end": p["end"], "summary": p["text"],
                    "kind": kind_of(p["support"], p["n"]), "support": f"{p['support']}/{p['n']}",
                    "segments": [{"start": s["start"], "text": s["text"],
                                  "kind": kind_of(s["support"], s["n"])} for s in inside]})
    return out


def pipeline_outline(progs: list[dict]) -> list[dict]:
    return [{"start": p["start"], "end": p["end"], "summary": p["summary"],
             "segments": [{"start": s, "text": t} for s, t in p["segments"]]} for p in progs]


def separators(progs: list[dict], file_end: float) -> list[dict]:
    """Gaps between pipeline programmes are separators the pipeline excised
    (derived by subtraction — see README, 'Separators are derived, not read')."""
    gaps, cursor = [], 0
    for p in progs:
        if p["start"] - cursor >= 1:
            gaps.append((cursor, p["start"]))
        cursor = max(cursor, p["end"])
    if file_end - cursor >= 1:
        gaps.append((cursor, int(file_end)))
    return [{"start": a, "end": b, "text": f"@sep Separator (excised) · {int(b - a)} s"} for a, b in gaps]


# -- existing-vs-predicted comparison ----------------------------------------

STOP = set("the and with for from that this was were are has had his her their its into over after before "
           "about than then when which while who whom whose onto upon some also been being".split())


def _words(s: str | None) -> set[str]:
    return {w for w in re.findall(r"[a-z]{3,}", (s or "").lower()) if w not in STOP}


def _squash(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _uniq(vals) -> list[str]:
    return list(dict.fromkeys(v for v in vals if v))


def _join(vals, sep="; ") -> str | None:
    """Distinct values, order kept; ';'-separated lists are split first so the same
    place or keyword given for two programmes appears once."""
    vals = _uniq(v.strip() for val in vals if val for v in str(val).split(";"))
    return sep.join(vals) if vals else None


def judge(key: str, existing: str | None, predicted: str | None) -> str:
    """Indicative only: match / close / differs, or added / missing / none when
    one side (or both) is empty. Simple rules — a prompt for the room, not a score."""
    if not existing and not predicted:
        return "none"
    if not predicted:
        return "missing"
    if not existing:
        return "added"
    if key == "year":
        have = {int(y) for y in re.findall(r"\d{4}", existing)}
        want = {int(y) for y in re.findall(r"\d{4}", predicted)}
        if not have or not want:
            return "differs"
        return "match" if want <= have else "close" if any(abs(a - b) <= 5 for a in have for b in want) else "differs"
    if key == "colour":
        norm = lambda v: "bw" if re.search(r"b/?w|black", v.lower()) else v.lower().split()[0]
        return "match" if norm(existing) == norm(predicted) else "differs"
    if key in ("title", "place"):
        ratio = difflib.SequenceMatcher(None, _squash(existing), _squash(predicted)).ratio()
        shared = _words(existing) & _words(predicted)
        return "match" if ratio >= 0.9 else "close" if ratio >= 0.5 or shared else "differs"
    if key in ("synopsis", "category", "keywords"):
        return "text"  # different kinds of text; the UI highlights shared words instead
    a, b = _words(existing), _words(predicted)
    overlap = len(a & b) / min(len(a), len(b)) if a and b else 0
    return "close" if overlap >= 0.25 else "differs"


def label_rows(progs: list[dict], ref: str, matches: dict) -> tuple[str | None, str]:
    lines, ranks = [], []
    for i, p in enumerate(progs, 1):
        m = matches.get((ref, p["kdl_prog"]))
        if not m or not m["ranked"]:
            continue
        rank = next((n for n, (_, _, t) in enumerate(m["ranked"], 1) if t), None)
        ranks.append(rank)
        top = m["ranked"][0]
        said = f"BFI label ranked #{rank}" if rank else "BFI label not in top 10"
        lines.append(f"P{i}: {said} · closest “{top[1]}” {top[0]:.0f}%")
    if not ranks:
        return None, "none"
    best = min((r for r in ranks if r), default=None)
    return "\n".join(lines), "match" if best == 1 else "close" if best else "differs"


def comparison(ref: str, cat: dict, fv: dict, progs: list[dict], matches: dict) -> tuple[list[dict], list[dict]]:
    """Mirrored rows (existing | predicted), then pipeline-only extras."""
    is_h22 = cat["batch"] == "H22"
    multi = len(progs) > 1
    per_prog = lambda key: ("\n".join(f"P{i}: {p[key]}" for i, p in enumerate(progs, 1) if p[key])
                            if multi else progs[0][key]) or None
    pred = {
        "title": _join([p["title"] for p in progs]),
        "year": _join(p["year"] for p in progs),
        "colour": _join(p["colour"] for p in progs),
        "sound": None,  # the pipeline does not target sound
        "category": _join(c for p in progs for c in (p["category"], p["category2"])),
        "place": _join(p["places"] for p in progs),
        "synopsis": per_prog("synopsis"),
        "keywords": _join((p["keywords"] for p in progs)),
    }
    exist = {
        "title": cat["label"] if is_h22 else cat["title"], "year": cat["year"], "colour": cat["colour"],
        "sound": cat["sound"], "category": fv.get("category"), "place": fv.get("place"),
        "synopsis": fv.get("synopsis"), "keywords": fv.get("keywords"),
    }
    labels = {"title": "Title", "year": "Year", "colour": "Colour", "sound": "Sound", "category": "Category",
              "place": "Place", "synopsis": "Synopsis", "keywords": "Keywords"}
    rows = []
    for key, label in labels.items():
        row = {"key": key, "left_label": label, "left": exist[key], "right_label": label,
               "right": pred[key], "status": judge(key, exist[key], pred[key])}
        if key == "title" and is_h22:
            right, status = label_rows(progs, ref, matches)
            row.update(left_label="Label on the tape", right_label="Label matches", right=right, status=status)
        rows.append(row)
    extras = [
        {"label": "Summary", "right": per_prog("summary")},
        {"label": "Credits", "right": per_prog("credits")},
        {"label": "Fiction", "right": _join(p["fiction"] for p in progs)},
    ]
    if is_h22:
        extras.insert(0, {"label": "Title (predicted)", "right": pred["title"]})
    return rows, [e for e in extras if e["right"]]


# -- records -----------------------------------------------------------------

def track(name: str, items: list[dict]) -> dict:
    return {"name": name, "items": items}


def label_lines(progs: list[dict], ref: str, matches: dict) -> list[str]:
    text, _ = label_rows(progs, ref, matches)
    return text.splitlines() if text else []


def annotator_lines(annotators: list[dict], ref: str) -> list[str]:
    lines = []
    for a in annotators:
        ans, progs = a["answers"].get(ref, {}), a["programmes"].get(ref, [])
        bits = [f"{len(progs)} programme{'s' if len(progs) != 1 else ''}"]
        if ans.get("label_matches"):
            bits.append(f"label matches content: {ans['label_matches']}")
        if ans.get("notes"):
            bits.append(f"“{ans['notes']}”")
        lines.append(f"{a['name']}: " + " · ".join(bits))
    return lines


def build_record(ref: str, cat: dict, progs: list[dict], annotators: list[dict],
                 matches: dict, video: Path | None, fv: dict | None = None) -> dict:
    fv = fv or {}
    n = len(annotators)
    c_progs, c_segs = cluster_programmes(annotators, ref), cluster_segments(annotators, ref)
    dur = video_duration(video) if video else None
    seg_items = [{"start": s, "text": t} for p in progs for s, t in p["segments"]]
    prog_items = [{"start": p["start"], "end": p["end"], "text": f"P{i} · {p['summary'][:140]}"}
                  for i, p in enumerate(progs, 1)]
    all_ends = [p["end"] for p in progs] + [c["end"] for c in c_progs]
    end = dur or max(all_ends or [0])
    tracks = []
    if n:
        tracks.append(track("human:Annotators · programmes" + (" (consensus)" if n > 1 else ""), [
            {"start": c["start"], "end": c["end"],
             "text": tag(kind_of(c["support"], n), f"P{i} · {c['support']}/{n} · {c['text']}" if n > 1 else f"P{i} · {c['text']}")}
            for i, c in enumerate(c_progs, 1)]))
        tracks.append(track("human:Annotators · segments" + (" (consensus)" if n > 1 else ""), [
            {"start": s["start"], "text": tag(kind_of(s["support"], n), s["text"])} for s in c_segs]))
    tracks.append(track("pipe:Pipeline · programmes", sorted(prog_items + separators(progs, end), key=lambda i: i["start"])))
    tracks.append(track("pipe:Pipeline · segments", seg_items))
    if n > 1:
        for a in annotators:
            ap = a["programmes"].get(ref, [])
            tracks.append(track(f"ann:{a['name']} · programmes", [
                {"start": p["start"], "end": p["end"], "text": f"P{p['no'] or i} · {p['text']}"}
                for i, p in enumerate(ap, 1) if p["end"] is not None]))
            tracks.append(track(f"ann:{a['name']} · segments", [
                {"start": s, "text": t} for p in ap for s, t in p["segments"]]))
    media = {"src": str(video) if video else f"missing/{ref}.mp4", "start": 0, "end": end,
             "label": "Whole file", "tracks": [t for t in tracks if t["items"]]}
    rows, extras = comparison(ref, cat, fv, progs, matches)
    agreed = sum(1 for c in c_progs if c["support"] == n)
    agreement = (f"{agreed} of {len(c_progs)} programmes agreed by all {n} annotators (±{TOL} s)"
                 if n > 1 and c_progs else None)
    is_h22 = cat["batch"] == "H22"
    return {
        "id": ref.replace(" ", "-"),
        "extraction": {
            "types": _uniq(c for p in progs for c in (p["category"], p["category2"])),
            "programmes": [f"P{i} · {fmt(p['start'])} · {int(p['end'] - p['start'])}s — {p['summary']}"
                           for i, p in enumerate(progs, 1)],
            "label_matches": label_lines(progs, ref, matches) if is_h22 else None,
            "compare": rows, "extras": extras, "outline": pipeline_outline(progs),
        },
        "ground_truth": {
            "title": f"{cat['label']}  (label on the tape)" if is_h22 else cat["title"],
            "year": cat["year"], "colour": cat["colour"], "sound": cat["sound"],
            "duration": cat["catalogue_duration"],
            "annotator_notes": annotator_lines(annotators, ref) or None,
            "agreement": agreement,
            "outline": human_outline(c_progs, c_segs) if n else None,
            "collection": COLLECTION.get(cat["batch"], cat["batch"]),
            "filename": video.name.replace(".pocket", "") if video else None,
            "file_duration": fmt(dur) if dur else None,
        },
        "metadata": {"media": media},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", type=Path, default=META / "predictions-10.v3.xlsx")
    ap.add_argument("--template", type=Path, default=META / "NWFA_annotation_TEMPLATE_v0.1.xlsx")
    ap.add_argument("--fv-catalogue", type=Path, default=FV_CAT)
    ap.add_argument("--annotations", type=Path, nargs="*",
                    default=sorted(p for p in META.glob("NWFA_annotation_*.xlsx") if "TEMPLATE" not in p.name))
    ap.add_argument("--labels", type=Path, default=LABELS_DOCX)
    ap.add_argument("--videos", type=Path, default=VIDEOS)
    a = ap.parse_args()

    preds, cats = load_predictions(a.predictions), load_catalogue(a.template)
    fvs = load_fv_catalogue(a.fv_catalogue)
    annotators = [load_annotator(p) for p in a.annotations]
    matches = load_label_matches(a.labels)
    missing = sorted(set(cats) - set(preds))
    if missing:
        raise SystemExit(f"no predictions for {missing}")

    print(json.dumps({"_provenance": {"project": "issa-ws2", "model": "FrameSense + Qwen3.8-27B",
                                      "annotators": [x["name"] for x in annotators]}}))
    for ref, cat in cats.items():
        print(json.dumps(build_record(ref, cat, preds[ref], annotators, matches, find_video(a.videos, ref),
                                      fvs.get(ref)), ensure_ascii=False))


if __name__ == "__main__":
    main()
