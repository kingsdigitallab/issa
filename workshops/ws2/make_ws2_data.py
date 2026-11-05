#!/usr/bin/env python3
"""Generate the aggregate JSON files that drive the WS2 (NWFA) explainer page.

Inputs are the two NWFA catalogue exports plus whatever pipeline prediction
file the current run has produced. The script is deliberately stage-agnostic:
point it at a 10-video prediction file now, a 15/20-video one after the
preparatory calls, and the full 400-video one before the workshop. The page
re-renders from the JSON without edits -- only the numbers and the stage
badges change.

Usage
-----
    python make_ws2_data.py \
        --channelm   "Channel M ISSA.xlsx" \
        --fvcat      "ISSA FV Cat data.xlsx" \
        --predictions "predictions-10.v1.xlsx" \
        --out        .

Optional
--------
    --humantruth kdl_sample10_annotated.xlsx   # NWFA validation sample
    --stage      first-pass | validated | full # default: inferred from scale
    --run        v1                            # default: from predictions name

Outputs
-------
    nwfa_metadata_data.json     catalogue aggregates (both collections)
    issa_ws2_predictions.json   pipeline aggregates for this run
    issa_ws2_humantruth.json    validation comparison (scaffold until call 2)

Provenance note: `issa_ws2_predictions.json` carries short model-written
content gists for the sampled videos only, because section 2 of the page (the
barcode mismatch) cannot be made without them. Everything else in both files
is aggregate counts. At full scale the gists are dropped and only the counts
remain -- see `--no-gists`.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------
# constants describing the NWFA material
# --------------------------------------------------------------------------

CM = "channelm"          # Channel M / Heritage 2022 batch
FV = "fv"                # Film & Video main catalogue batch

COLLECTION_META = {
    CM: {
        "id": CM,
        "name": "Channel M",
        "long_name": "Channel M (Heritage 2022)",
        "file_count": 200,
        "blurb": (
            "The entire news and music output of Channel M, an early Manchester "
            "local TV station that closed in 2012. Some complete news programmes, "
            "but mostly rushes tapes and raw footage. 1,689 tapes were digitised "
            "under Heritage 2022, around 35% of the collection."
        ),
        "caveat": (
            "A printing error on the barcodes means the label information in the "
            "metadata does not match up with the file content."
        ),
    },
    FV: {
        "id": FV,
        "name": "Film & Video",
        "long_name": "Film & Video main catalogue",
        "file_count": 200,
        "blurb": (
            "A deliberately broad range from NWFA's main film and video collection: "
            "professional and amateur, b/w and colour, sound and silent, from film, "
            "video and born-digital originals. Full catalogue metadata from NWFA's "
            "FileMaker Pro database."
        ),
        "caveat": None,
    },
}

# Frames per foot, by gauge, used to derive the projection speed the catalogue
# running times imply. Approximate and only used descriptively.
FRAMES_PER_FOOT = {
    "35mm N": 16, "35mm S": 16, "16mm": 40,
    "std8mm": 80, "spr8mm": 72, "9.5mm": 50,
}

# Comparable descriptive fields, mapped onto each catalogue's own column names.
# None means the collection has no column for it at all.
FIELD_CROSSWALK = [
    ("title",      "Title",            "title"),
    ("year",       "Date",             "dates"),
    ("synopsis",   "Synopsis",         "synopsis"),
    ("keywords",   "Subject",          "index_terms"),
    ("genre",      "Genre",            "category"),
    ("place",      "Production Country", "ContentCounty"),
    ("colour",     "Colour",           "colour"),
    ("sound",      "Sound",            "sound"),
    ("duration",   "Tape duration (mins)", "running_time_mns"),
    ("credits",    "Director",         "producer"),
]

# Prediction fields whose completeness the page reports.
PRED_FIELDS = ["title", "year", "place", "colour", "types", "fiction",
               "summary", "synopsis", "segments", "credits", "keywords"]

# Clips at or below this many seconds that sit between two detected separators
# are almost certainly separator residue rather than programmes.
NONCONTENT_MAX_SECONDS = 10

NONCONTENT_PHRASES = [
    "colour bar", "color bar", "test pattern", "test card", "test signal",
    "blank black", "blank grey", "blank screen", "grey screen",
    "no identifiable", "white noise", "static",
]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def tidy_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse the newlines and double spaces in the supplier's headers."""
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
    return df


def read_sheet(path: str | Path) -> pd.DataFrame:
    return tidy_columns(pd.read_excel(path, dtype=str))


def filled(series: pd.Series) -> int:
    """Count values that are present and not an empty / placeholder string."""
    if series is None:
        return 0
    s = series.dropna().astype(str).str.strip()
    return int((~s.isin(["", "/", "-", "nan", "None"])).sum())


def pct(n: int, total: int) -> float:
    return round(100.0 * n / total, 1) if total else 0.0


def split_terms(value) -> list[str]:
    """NWFA multi-valued fields separate terms with newlines or pipes."""
    if pd.isna(value):
        return []
    parts = re.split(r"[\n|]", str(value))
    return [p.strip() for p in parts if p.strip()]


def counter_to_sorted(c: Counter, limit: int | None = None) -> list[dict]:
    items = [{"label": k, "n": v} for k, v in c.most_common(limit)]
    return items


def histogram(values, edges) -> dict:
    """Bucket values into [edges[i], edges[i+1]) with a final open bucket."""
    counts = [0] * len(edges)
    for v in values:
        placed = False
        for i in range(len(edges) - 1):
            if edges[i] <= v < edges[i + 1]:
                counts[i] += 1
                placed = True
                break
        if not placed and v >= edges[-1]:
            counts[-1] += 1
    labels = [f"{edges[i]}–{edges[i+1]}" for i in range(len(edges) - 1)]
    labels.append(f"{edges[-1]}+")
    return {"labels": labels, "counts": counts}


def describe(values) -> dict:
    s = pd.Series(list(values), dtype="float64").dropna()
    if s.empty:
        return {"n": 0}
    return {
        "n": int(s.size),
        "min": round(float(s.min()), 1),
        "median": round(float(s.median()), 1),
        "mean": round(float(s.mean()), 1),
        "max": round(float(s.max()), 1),
    }


def tokenise(text) -> set[str]:
    """Lowercase alphabetic tokens, crudely de-pluralised, stopwords dropped."""
    if pd.isna(text):
        return set()
    txt = unicodedata.normalize("NFKD", str(text)).lower()
    raw = re.findall(r"[a-z]{3,}", txt)
    stop = {"and", "the", "for", "with", "from", "this", "that", "its",
            "are", "was", "were", "has", "have", "into", "out", "off",
            "one", "two", "all", "any", "not", "but", "his", "her", "their"}
    out = set()
    for w in raw:
        if w in stop:
            continue
        if w.endswith("ies") and len(w) > 4:
            w = w[:-3] + "y"
        elif w.endswith("sses"):
            w = w[:-2]
        elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            w = w[:-1]
        out.add(w)
    return out


# --------------------------------------------------------------------------
# catalogue aggregates
# --------------------------------------------------------------------------

def channelm_aggregates(cm: pd.DataFrame) -> dict:
    n = len(cm)
    fill = {c: filled(cm[c]) for c in cm.columns}
    label = cm["Label transcription"] if "Label transcription" in cm else pd.Series(dtype=str)
    words = label.dropna().astype(str).str.split().str.len()

    descriptive_cols = [
        "Title", "Content description", "Fiction / Non Fiction / Both", "Genre",
        "Subject", "Date", "Synopsis", "Sound", "Colour", "Language",
        "Approximate Duration - Minutes", "Series Title", "Work Type",
        "Production Company", "Director", "Broadcast Channel", "Tape duration (mins)",
    ]
    present = [c for c in descriptive_cols if c in cm.columns]

    return {
        "rows": n,
        "columns_total": int(cm.shape[1]),
        "columns_populated": int(sum(1 for v in fill.values() if v > 0)),
        "columns_empty": int(sum(1 for v in fill.values() if v == 0)),
        "populated_columns": [c for c in cm.columns if fill[c] > 0],
        "descriptive_columns_checked": len(present),
        "descriptive_columns_empty": int(sum(1 for c in present if fill[c] == 0)),
        "tape_format": dict(Counter(cm["Tape format"].dropna()).most_common()) if "Tape format" in cm else {},
        "crates": dict(Counter(cm["Crate barcode"].dropna()).most_common()) if "Crate barcode" in cm else {},
        "digitisation_dates": sorted({str(d)[:10] for d in cm["Digitisation Date"].dropna()}) if "Digitisation Date" in cm else [],
        "label": {
            "present": filled(label),
            "words": describe(words),
            "with_date_fragment": int(label.str.contains(r"\d{1,2}[/.]\d{1,2}", na=False).sum()) if len(label) else 0,
            "distinct": int(label.nunique(dropna=True)) if len(label) else 0,
        },
    }


def fv_aggregates(fv: pd.DataFrame) -> dict:
    n = len(fv)
    fill = {c: filled(fv[c]) for c in fv.columns}

    secs = (pd.to_numeric(fv.get("running_time_mns"), errors="coerce") * 60
            + pd.to_numeric(fv.get("running_time_scs"), errors="coerce"))
    years = pd.to_numeric(
        fv.get("FilmCatDate", pd.Series(dtype=str)).astype(str).str.extract(r"(\d{4})")[0],
        errors="coerce")
    decades = (years // 10 * 10).dropna().astype(int)

    cat_terms = Counter()
    for v in fv.get("category", pd.Series(dtype=str)):
        cat_terms.update(split_terms(v))
    prof_terms, am_terms = Counter(), Counter()
    for v in fv.get("ProfCategories", pd.Series(dtype=str)):
        prof_terms.update(split_terms(v))
    for v in fv.get("AmCategories", pd.Series(dtype=str)):
        am_terms.update(split_terms(v))

    gauge = fv.get("original gauge", pd.Series(dtype=str)).astype(str).str.strip()
    implied = {}
    ft = pd.to_numeric(fv.get("length of master"), errors="coerce")
    for g, idx in gauge.groupby(gauge).groups.items():
        fpf = FRAMES_PER_FOOT.get(g)
        if not fpf:
            continue
        v = (ft.loc[idx] * fpf / secs.loc[idx]).dropna()
        v = v[(v > 5) & (v < 60)]
        if len(v) >= 4:
            implied[g] = {"n": int(len(v)), "median_fps": round(float(v.median()), 1)}

    return {
        "rows": n,
        "columns_total": int(fv.shape[1]),
        "columns_populated": int(sum(1 for v in fill.values() if v > 0)),
        "columns_full": int(sum(1 for v in fill.values() if v == n)),
        "columns_empty": int(sum(1 for v in fill.values() if v == 0)),
        "colour": dict(Counter(x.strip() for x in fv.get("colour", pd.Series(dtype=str)).dropna()).most_common()),
        "sound": dict(Counter(x.strip() for x in fv.get("sound", pd.Series(dtype=str)).dropna()).most_common()),
        "gauge": dict(Counter(x for x in gauge if x and x != "nan").most_common()),
        "prof_am": dict(Counter(fv.get("Professional", pd.Series(dtype=str)).dropna()).most_common()),
        "category_terms": counter_to_sorted(cat_terms),
        "prof_categories": counter_to_sorted(prof_terms),
        "am_categories": counter_to_sorted(am_terms),
        "content_county_top": counter_to_sorted(
            Counter(fv.get("ContentCounty", pd.Series(dtype=str)).dropna()), 10),
        "decades": {str(k): int(v) for k, v in sorted(Counter(decades).items())},
        "years": {"min": int(years.min()) if years.notna().any() else None,
                  "max": int(years.max()) if years.notna().any() else None},
        "runtime_minutes": describe(secs / 60),
        "runtime_hours_total": round(float(secs.sum() / 3600), 1),
        "runtime_over_30min": int((secs > 1800).sum()),
        "runtime_under_5min": int((secs < 300).sum()),
        "synopsis_words": describe(fv.get("synopsis", pd.Series(dtype=str)).astype(str).str.split().str.len()),
        "index_terms_count": describe(fv.get("index_terms", pd.Series(dtype=str)).astype(str).str.split().str.len()),
        "implied_projection_fps": implied,
    }


def build_metadata_json(cm: pd.DataFrame, fv: pd.DataFrame, sample_ids: dict) -> dict:
    completeness = []
    for key, cm_col, fv_col in FIELD_CROSSWALK:
        completeness.append({
            "field": key,
            CM: pct(filled(cm[cm_col]) if cm_col in cm.columns else 0, len(cm)),
            FV: pct(filled(fv[fv_col]) if fv_col in fv.columns else 0, len(fv)),
            "cm_column": cm_col if cm_col in cm.columns else None,
            "fv_column": fv_col if fv_col in fv.columns else None,
        })

    cm_agg = channelm_aggregates(cm)
    fv_agg = fv_aggregates(fv)

    collections = []
    for cid, agg in ((CM, cm_agg), (FV, fv_agg)):
        meta = dict(COLLECTION_META[cid])
        meta["columns_total"] = agg["columns_total"]
        meta["columns_populated"] = agg["columns_populated"]
        meta["columns_empty"] = agg["columns_empty"]
        collections.append(meta)

    # Hierarchy bands: what each catalogue establishes on its own, at each level.
    # value = share of the 400 files; state = verified / assumed / check / unknown
    hierarchy = {
        "levels": [
            {"level": "Archive", "note": "NWFA",
             "bands": [{"collection": "archive", "share": 100, "state": "verified", "label": "NWFA"}]},
            {"level": "Collection", "note": "2 batches of 200",
             "bands": [{"collection": CM, "share": 50, "state": "verified", "label": "Channel M"},
                       {"collection": FV, "share": 50, "state": "verified", "label": "Film & Video"}]},
            {"level": "Video file", "note": "400 delivered files",
             "bands": [{"collection": CM, "share": 50, "state": "verified", "label": "200 files"},
                       {"collection": FV, "share": 50, "state": "verified", "label": "200 files"}]},
            {"level": "Programme", "note": "what the catalogue says is in each file",
             "bands": [{"collection": CM, "share": 50, "state": "check",
                        "label": "label only, unreliable"},
                       {"collection": FV, "share": 50, "state": "assumed",
                        "label": "assumed 1 film = 1 programme"}]},
            {"level": "Segment", "note": "structure inside a programme",
             "bands": [{"collection": CM, "share": 50, "state": "unknown", "label": "none"},
                       {"collection": FV, "share": 50, "state": "assumed",
                        "label": "prose synopsis, no timecodes"}]},
        ],
        "sample": {
            "n": sum(len(v) for v in sample_ids.values()),
            "items": ([{"id": i, "collection": CM, "annotated": False} for i in sample_ids.get(CM, [])]
                      + [{"id": i, "collection": FV, "annotated": False} for i in sample_ids.get(FV, [])]),
        },
    }

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
        "totals": {"files": len(cm) + len(fv), CM: len(cm), FV: len(fv)},
        "collections": collections,
        "completeness": completeness,
        CM: cm_agg,
        FV: fv_agg,
        "hierarchy": hierarchy,
    }


# --------------------------------------------------------------------------
# prediction aggregates
# --------------------------------------------------------------------------

def parse_kdl_prog(value: str) -> tuple[int, int]:
    """`HH.MM.SS-DDD` -> (start seconds, duration seconds)."""
    m = re.match(r"(\d+)\.(\d+)\.(\d+)-(\d+)", str(value))
    if not m:
        raise ValueError(f"unrecognised kdl_prog value: {value!r}")
    h, mi, s, d = (int(x) for x in m.groups())
    return h * 3600 + mi * 60 + s, d


def classify_collection(prefix: str) -> str:
    return CM if str(prefix).strip().startswith("N_") else FV


def file_key(prefix: str) -> str:
    """Stable per-file key from the prediction file's prefix column."""
    p = str(prefix).strip()
    m = re.match(r"(N_\d+)", p)
    if m:
        return m.group(1)
    m = re.match(r"(NWFA\s+\d+)", p)
    return m.group(1) if m else p


def looks_noncontent(row, duration: int, bounded_by_separators: bool) -> bool:
    text = f"{row.get('summary','')} {row.get('synopsis','')}".lower()
    phrase_hit = any(p in text for p in NONCONTENT_PHRASES)
    if duration <= NONCONTENT_MAX_SECONDS and (phrase_hit or bounded_by_separators):
        return True
    return duration <= 2 and phrase_hit


def build_predictions_json(pred: pd.DataFrame, cm: pd.DataFrame, fv: pd.DataFrame,
                           run: str, stage: str | None, include_gists: bool) -> dict:
    pred = pred.copy()
    pred["fkey"] = pred["DODfilenameprefix"].map(file_key)
    pred["collection"] = pred["DODfilenameprefix"].map(classify_collection)
    pred[["start", "dur"]] = pred["kdl_prog"].apply(
        lambda v: pd.Series(parse_kdl_prog(v)))
    pred["end"] = pred["start"] + pred["dur"]
    pred = pred.sort_values(["fkey", "start"]).reset_index(drop=True)

    n_files = pred["fkey"].nunique()
    stage = stage or ("full" if n_files >= 300 else
                      "validated" if n_files >= 15 else "first-pass")

    # ---- per-file structure, separators derived from the gaps between clips
    files, separators, noncontent = [], [], []
    for fkey, g in pred.groupby("fkey", sort=True):
        g = g.sort_values("start")
        coll = g["collection"].iloc[0]
        span = int(g["end"].max())
        covered = int(g["dur"].sum())

        gaps = []
        if g["start"].iloc[0] > 0:
            gaps.append({"at": 0, "seconds": int(g["start"].iloc[0]), "leading": True})
        prev_end = None
        for _, r in g.iterrows():
            if prev_end is not None and r["start"] > prev_end:
                gaps.append({"at": int(prev_end),
                             "seconds": int(r["start"] - prev_end),
                             "leading": False})
            prev_end = r["end"]
        for gp in gaps:
            separators.append({"file": fkey, "collection": coll, **gp})

        sep_edges = {gp["at"] for gp in gaps} | {gp["at"] + gp["seconds"] for gp in gaps}
        for _, r in g.iterrows():
            bounded = r["start"] in sep_edges and r["end"] in sep_edges
            if looks_noncontent(r, int(r["dur"]), bounded):
                item = {"file": fkey, "collection": coll, "prog": str(r["vid.prog"]),
                        "start": int(r["start"]), "seconds": int(r["dur"]),
                        "types": r.get("types"), "bounded_by_separators": bool(bounded)}
                if include_gists:
                    item["gist"] = str(r.get("summary", ""))[:160]
                noncontent.append(item)

        files.append({
            "file": fkey, "collection": coll,
            "span_seconds": span, "covered_seconds": covered,
            "coverage": round(covered / span, 3) if span else None,
            "clips": int(len(g)),
            "separators": len(gaps),
            "leading_separator": int(g["start"].iloc[0]) if g["start"].iloc[0] > 0 else 0,
        })

    # ---- programmes per file, by collection
    per_file = {}
    for coll in (CM, FV):
        counts = [f["clips"] for f in files if f["collection"] == coll]
        if not counts:
            per_file[coll] = {"labels": [], "counts": [], "n": 0}
            continue
        c = Counter(counts)
        labels = sorted(c)
        per_file[coll] = {
            "labels": [str(x) for x in labels],
            "counts": [c[x] for x in labels],
            **describe(counts),
        }

    # ---- durations of proposed programmes
    duration = {}
    for coll in (CM, FV):
        d = pred.loc[pred["collection"] == coll, "dur"]
        duration[coll] = {
            **describe(d / 60),
            "hist": histogram((d / 60).tolist(), [0, 1, 2, 5, 10, 20, 30, 45, 60]),
            "under_10_s": int((d <= 10).sum()),
            "over_30_min": int((d > 1800).sum()),
        }

    # ---- separator statistics
    sep_secs = [s["seconds"] for s in separators]
    separator_block = {
        "n": len(separators),
        "leading": sum(1 for s in separators if s["leading"]),
        "files_with_any": len({s["file"] for s in separators}),
        "by_collection": {c: sum(1 for s in separators if s["collection"] == c) for c in (CM, FV)},
        "seconds": describe(sep_secs),
        "hist": histogram(sep_secs, [0, 5, 10, 20, 30, 45, 60, 90]),
        "derived_from": "gaps between consecutive clips in the predictions file",
        "items": separators,
    }

    # ---- coverage
    cov = [f["coverage"] for f in files if f["coverage"] is not None]
    coverage_block = {
        **describe([c * 100 for c in cov]),
        "hist": histogram([c * 100 for c in cov], [80, 85, 90, 95, 99, 100]),
        "files_below_95pct": sum(1 for c in cov if c < 0.95),
        "per_file": files,
    }

    # ---- non-content clips
    noncontent_block = {
        "n": len(noncontent),
        "of_programmes": int(len(pred)),
        "pct": pct(len(noncontent), len(pred)),
        "median_seconds": describe([x["seconds"] for x in noncontent]).get("median"),
        "bounded_by_separators": sum(1 for x in noncontent if x["bounded_by_separators"]),
        "spurious_types": dict(Counter(
            t.strip() for x in noncontent for t in str(x["types"]).split(";") if t.strip()
        ).most_common()),
        "items": noncontent,
    }

    # ---- field completeness of the machine output
    completeness = []
    for field in PRED_FIELDS:
        row = {"field": field}
        for coll in (CM, FV):
            sub = pred[pred["collection"] == coll]
            row[coll] = pct(filled(sub[field]) if field in sub else 0, len(sub))
        completeness.append(row)

    # ---- vocabularies
    machine_types = Counter()
    for v in pred["types"].dropna():
        machine_types.update(t.strip() for t in str(v).split(";") if t.strip())
    machine_places = Counter()
    for v in pred["place"].dropna():
        machine_places.update(t.strip() for t in str(v).split(";") if t.strip())

    cat_terms = Counter()
    for v in fv.get("category", pd.Series(dtype=str)):
        cat_terms.update(split_terms(v))

    # keyword overlap against index_terms, for the sampled FV films only
    overlap = []
    for fkey, g in pred[pred["collection"] == FV].groupby("fkey"):
        acc = fkey.replace("NWFA", "").strip()
        match = fv[fv["accession number"].astype(str).str.strip() == acc]
        if match.empty:
            continue
        cat_tokens = tokenise(match.iloc[0].get("index_terms"))
        kw_raw = [k.strip() for k in str(g.iloc[0].get("keywords", "")).split(";") if k.strip()]
        kw_tokens = tokenise(" ".join(kw_raw))
        strict = len({k.lower() for k in kw_raw} & {t for t in cat_tokens})
        overlap.append({
            "file": fkey,
            "catalogue_tokens": len(cat_tokens),
            "machine_terms": len(kw_raw),
            "machine_tokens": len(kw_tokens),
            "shared_tokens": len(cat_tokens & kw_tokens),
            "shared_terms_strict": strict,
        })

    vocab_block = {
        "machine_types": counter_to_sorted(machine_types),
        "machine_places": counter_to_sorted(machine_places, 12),
        "nwfa_category_terms": counter_to_sorted(cat_terms),
        "keyword_overlap": overlap,
        "keyword_overlap_totals": {
            "catalogue_tokens": sum(o["catalogue_tokens"] for o in overlap),
            "machine_tokens": sum(o["machine_tokens"] for o in overlap),
            "shared_tokens": sum(o["shared_tokens"] for o in overlap),
        },
    }

    # ---- inner segments
    seg_counts = []
    unparseable = 0
    for v in pred["segments"]:
        if pd.isna(v):
            seg_counts.append(0)
            continue
        parts = [p for p in str(v).split(";") if p.strip()]
        seg_counts.append(len(parts))
        unparseable += sum(1 for p in parts if not re.search(r"\d{1,2}:\d{2}", p))
    pred["n_segments"] = seg_counts
    segments_block = {
        "total_items": int(sum(seg_counts)),
        "programmes_without": int(sum(1 for x in seg_counts if x == 0)),
        "unparseable_items": int(unparseable),
        "timecode_styles": dict(Counter(
            ("HH:MM:SS" if re.search(r"\d{1,2}:\d{2}:\d{2}", str(v)) else
             "MM:SS" if re.search(r"\d{1,2}:\d{2}", str(v)) else "none")
            for v in pred["segments"]).most_common()),
    }
    for coll in (CM, FV):
        sub = pred[pred["collection"] == coll]["n_segments"]
        segments_block[coll] = {**describe(sub),
                                "hist": histogram(sub.tolist(), [0, 1, 2, 4, 6, 8, 12, 16])}

    # ---- label vs content, Channel M only
    labels = {}
    if "File name" in cm.columns and "Label transcription" in cm.columns:
        for _, r in cm.iterrows():
            labels[str(r["File name"]).split("_01of01")[0]] = r["Label transcription"]

    label_items = []
    for fkey, g in pred[pred["collection"] == CM].groupby("fkey"):
        content = g[g["dur"] > NONCONTENT_MAX_SECONDS].sort_values("dur", ascending=False)
        gist = str(content.iloc[0]["summary"]) if len(content) else ""
        item = {"file": fkey, "label": labels.get(fkey), "verdict": None,
                "programmes": int(len(g))}
        if include_gists:
            item["machine_gist"] = gist[:220]
        label_items.append(item)

    label_block = {
        "files": len(label_items),
        "verdicts_assigned": 0,
        "note": ("Verdicts are set by hand after a human has compared label and "
                 "content; left null until NWFA confirms."),
        "items": label_items,
    }

    # ---- duration cross-check against the FV catalogue
    dur_check = []
    for fkey, g in pred[pred["collection"] == FV].groupby("fkey"):
        acc = fkey.replace("NWFA", "").strip()
        match = fv[fv["accession number"].astype(str).str.strip() == acc]
        if match.empty:
            continue
        h = match.iloc[0]
        cat_s = (pd.to_numeric(h.get("running_time_mns"), errors="coerce") * 60
                 + pd.to_numeric(h.get("running_time_scs"), errors="coerce"))
        file_s = int(g["end"].max())
        if pd.isna(cat_s) or not cat_s:
            continue
        dur_check.append({
            "file": fkey,
            "gauge": str(h.get("original gauge", "")).strip(),
            "sound": str(h.get("sound", "")).strip(),
            "catalogue_seconds": int(cat_s),
            "file_seconds": file_s,
            "ratio": round(file_s / cat_s, 2),
        })
    duration_check_block = {
        "items": dur_check,
        "disagreeing": sum(1 for d in dur_check if abs(d["ratio"] - 1) > 0.05),
        "checked": len(dur_check),
    }

    # ---- example timelines: the most structured file in each collection
    examples = {}
    for coll in (CM, FV):
        cand = [f for f in files if f["collection"] == coll]
        if not cand:
            continue
        pick = max(cand, key=lambda f: (f["clips"], f["span_seconds"]))
        g = pred[pred["fkey"] == pick["file"]].sort_values("start")
        examples[coll] = {
            "file": pick["file"],
            "span_seconds": pick["span_seconds"],
            "clips": [{"start": int(r["start"]), "seconds": int(r["dur"]),
                       "prog": str(r["vid.prog"]),
                       "noncontent": any(x["prog"] == str(r["vid.prog"])
                                         and x["file"] == pick["file"]
                                         for x in noncontent)}
                      for _, r in g.iterrows()],
            "separators": [s for s in separators if s["file"] == pick["file"]],
        }

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
        "run": run,
        "stage": stage,
        "contains_model_text": bool(include_gists),
        "scale": {"files": n_files, "of": 400,
                  "by_collection": {c: sum(1 for f in files if f["collection"] == c)
                                    for c in (CM, FV)}},
        "totals": {
            "files": n_files,
            "programmes": int(len(pred)),
            "segment_items": segments_block["total_items"],
            "separators": separator_block["n"],
            "by_collection": {
                c: {"files": sum(1 for f in files if f["collection"] == c),
                    "programmes": int((pred["collection"] == c).sum())}
                for c in (CM, FV)},
        },
        "programmes_per_file": per_file,
        "duration": duration,
        "separators": separator_block,
        "coverage": coverage_block,
        "noncontent": noncontent_block,
        "completeness": completeness,
        "vocab": vocab_block,
        "segments": segments_block,
        "label_match": label_block,
        "duration_check": duration_check_block,
        "examples": examples,
    }


# --------------------------------------------------------------------------
# human-truth scaffold
# --------------------------------------------------------------------------

HUMANTRUTH_FIELDS = [
    {"field": "label_matches_content", "collections": [CM],
     "why": "The only field that addresses the barcode error. One verdict per tape."},
    {"field": "nb_progs", "collections": [CM, FV],
     "why": "No source holds this. The core outer-segmentation reference."},
    {"field": "prog_timecodes", "collections": [CM, FV],
     "why": "No source holds this. Lets us score boundary placement, not just counts."},
    {"field": "machine_text_verdict", "collections": [CM, FV],
     "why": "Accept / amend / reject on the machine summary, with a reason."},
    {"field": "year", "collections": [CM],
     "why": "Catalogued for Film & Video already; only needed for Channel M."},
    {"field": "colour", "collections": [CM], "why": "As above."},
    {"field": "sound", "collections": [CM], "why": "As above."},
]


def build_humantruth_json(path: str | Path | None, pred: pd.DataFrame) -> dict:
    block = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
        "status": "pending",
        "proposed_fields": HUMANTRUTH_FIELDS,
        "returned": 0,
        "expected": int(pred["DODfilenameprefix"].map(file_key).nunique()),
        "agreement": [],
        "items": [],
    }
    if not path:
        return block

    tpl = tidy_columns(pd.read_excel(path, dtype=str))
    returned = 0
    items = []
    # `title` is pre-populated by KDL from the filename / catalogue, so it is not
    # evidence that NWFA has annotated anything. Neither are the key columns.
    prefilled = {"KDLID", "batch", "prefix", "title"}
    for _, r in tpl.iterrows():
        vals = {c: (None if pd.isna(r[c]) else str(r[c])) for c in tpl.columns}
        answered = sum(1 for k, v in vals.items() if k not in prefilled and v)
        if answered:
            returned += 1
        items.append({"prefix": vals.get("prefix"), "batch": vals.get("batch"),
                      "fields_answered": answered})
    block["returned"] = returned
    block["items"] = items
    block["status"] = "partial" if 0 < returned < len(tpl) else (
        "complete" if returned and returned == len(tpl) else "pending")
    return block


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--channelm", required=True, help="Channel M ISSA.xlsx")
    ap.add_argument("--fvcat", required=True, help="ISSA FV Cat data.xlsx")
    ap.add_argument("--predictions", required=True,
                    help="pipeline predictions, one row per proposed programme (.xlsx or .csv)")
    ap.add_argument("--humantruth", default=None, help="NWFA validation sample (.xlsx)")
    ap.add_argument("--out", default=".", help="output directory")
    ap.add_argument("--run", default=None, help="run label, e.g. v1 (default: from filename)")
    ap.add_argument("--stage", default=None,
                    choices=["first-pass", "validated", "full"],
                    help="override the stage badge (default: inferred from file count)")
    ap.add_argument("--no-gists", action="store_true",
                    help="omit all model-written text (use at full scale)")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    cm = read_sheet(args.channelm)
    fv = read_sheet(args.fvcat)
    pred = (pd.read_csv(args.predictions, dtype=str)
            if str(args.predictions).lower().endswith(".csv")
            else read_sheet(args.predictions))

    run = args.run or (re.search(r"(v\d+)", Path(args.predictions).stem).group(1)
                       if re.search(r"(v\d+)", Path(args.predictions).stem) else "v1")

    sample_ids = {CM: [], FV: []}
    for p in pred["DODfilenameprefix"].map(file_key).unique():
        sample_ids[classify_collection(p)].append(p)

    meta = build_metadata_json(cm, fv, sample_ids)
    preds = build_predictions_json(pred, cm, fv, run, args.stage, not args.no_gists)
    human = build_humantruth_json(args.humantruth, pred)

    for name, payload in (("nwfa_metadata_data.json", meta),
                          ("issa_ws2_predictions.json", preds),
                          ("issa_ws2_humantruth.json", human)):
        target = out / name
        target.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {target}  ({target.stat().st_size:,} bytes)")

    print(f"\nstage={preds['stage']}  run={preds['run']}  "
          f"files={preds['scale']['files']}/400  "
          f"programmes={preds['totals']['programmes']}  "
          f"separators={preds['totals']['separators']}  "
          f"non-content={preds['noncontent']['n']} ({preds['noncontent']['pct']}%)")


if __name__ == "__main__":
    main()
