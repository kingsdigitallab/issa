"""Script created by opencode:e-research/arc:apex
Creates catalogue/predictions-400.v3.csv from the misc3 answers found under
./batches/**/clip_answers.json: one row per answered clip, with the misc3
keys and values as columns alongside DODfilenameprefix and kdl_prog. The
secondpass1 programme, bands and environment sub-answers are added as extra
columns.
"""

from pathlib import Path
import ast
import csv
import json
import re

BATCHES_DIR = Path("batches")
OUTPUT_PATH = Path("catalogue") / "predictions-400.v3.csv"
ANSWER_KEY = "misc3"
SECOND_PASS_KEY = "secondpass1"
SECOND_PASS_COLUMNS = ("programme", "bands", "environment")
NODATA = "NODATA"
DOD_PREFIX_COLUMN = "DODfilenameprefix"
KDL_PROG_COLUMN = "kdl_prog"
FIELDNAMES = [
    DOD_PREFIX_COLUMN,
    KDL_PROG_COLUMN,
    "title",
    "year",
    "places",
    "colour",
    "category",
    "category2",
    "fiction",
    "summary",
    "synopsis",
    "segments",
    "credits",
    "keywords",
    *SECOND_PASS_COLUMNS,
]
# SYNOPSIS_KEY_VARIANTS = ("Synopsis", " synopsis", "summary")
LIST_SEPARATOR = "; "
SEGMENT_SEPARATOR = "; "
CREDIT_SEPARATOR = "; "
BAND_SEPARATOR = "; "
ACTIVITY_SEPARATOR = "; "
FENCE_PATTERN = re.compile(r"^\s*```[A-Za-z0-9_-]*\s*|\s*```\s*$")


def normalize_answer(answer: dict) -> dict:
    """Answer dict with a variant synopsis key, if present, mapped onto 'synopsis'."""
    ret = {}
    for k, v in answer.items():
        ret[k.lower().strip()] = v
    # ret = dict(answer)
    # for variant in SYNOPSIS_KEY_VARIANTS:
    #     if variant in ret:
    #         ret["synopsis"] = ret.pop(variant)
    #         break
    return ret


def strip_fences(text: str) -> str:
    """Answer text with surrounding markdown code fences removed."""
    ret = FENCE_PATTERN.sub("", text)
    return ret


def salvage_answer(answer: str) -> dict | None:
    """Dict parsed from a string answer: fence-stripped, JSON first, Python literals as fallback."""
    ret = None
    text = strip_fences(answer)
    for parse in (json.loads, ast.literal_eval):
        try:
            parsed = parse(text)
        except (TypeError, ValueError, SyntaxError):
            continue
        if isinstance(parsed, dict):
            ret = parsed
            break
    return ret


def format_value(values, field=None) -> str:
    """Scalar value as a cell string, None as an empty string."""
    if values is None:
        return ""
    
    ret = values
    if field == 'segments':
        ret = format_segments(values)
    elif field == 'bands':
        ret = format_bands(values)
    else:
        if isinstance(ret, dict):
            ret = [f"{key}: {format_value(v)}" for key, v in ret.items()]
        if isinstance(ret, list):
            ret = LIST_SEPARATOR.join(format_value(v) for v in ret)
    
    return str(ret)

def format_segments(segments) -> str:
    """Segment dicts as 'time - title' entries joined with the segment separator."""
    if isinstance(segments, list):
        entries = [f"{seg.get('starting', '')}: {seg.get('title', '')}" for seg in segments]
        ret = SEGMENT_SEPARATOR.join(entries)
    else:
        ret = format_value(segments)
    return ret


def format_bands(bands) -> str:
    """Band dicts as 'name (activity; activity)' entries joined with the band separator."""
    ret = ""
    if isinstance(bands, list):
        entries = []
        for band in bands:
            if not isinstance(band, dict):
                entries.append(format_value(band))
                continue
            name = band.get("name") or ""
            activities = band.get("activities", [])
            if isinstance(activities, list):
                activity_text = ACTIVITY_SEPARATOR.join(format_value(a) for a in activities)
            else:
                activity_text = format_value(activities)
            entries.append(f"{name} ({activity_text})" if activity_text else str(name))
        ret = BAND_SEPARATOR.join(entries)
    else:
        ret = format_value(bands)
    return ret


# def format_credits(credits) -> str:
#     """Credits as readable text: dict to 'key: value' pairs, list joined, str as-is."""
#     ret = format_value(credits)
#     if isinstance(credits, dict):
#         pairs = [f"{key}: {format_list(value)}" for key, value in credits.items()]
#         ret = CREDIT_SEPARATOR.join(pairs)
#     elif isinstance(credits, list):
#         ret = CREDIT_SEPARATOR.join(format_value(credit) for credit in credits)
#     return ret


def row_for(path: Path, answer: dict, second_answer: dict | None = None) -> dict:
    """One CSV row for a clip answer file: clip identity columns plus misc3 and secondpass1 fields."""
    ret = {}
    for col in FIELDNAMES:
        if col in SECOND_PASS_COLUMNS:
            value = second_answer.get(col, NODATA) if isinstance(second_answer, dict) else NODATA
            if value is None:
                value = NODATA
        else:
            value = answer.get(col, None)
        if col == "programme" and isinstance(value, bool):
            value = str(value).lower()
        ret[col] = format_value(value, col)
    ret[DOD_PREFIX_COLUMN] = path.parent.parent.name.removesuffix(".32")
    ret[KDL_PROG_COLUMN] = "-".join(path.parent.name.split("-")[:2])

    return ret


def main() -> int:
    """Write catalogue/predictions-400.v3.csv from the misc3 and secondpass1 answers and report the outcome."""
    ret = 0
    rows = 0
    seen = 0
    missing = 0
    salvaged = 0
    invalid = 0
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for path in sorted(BATCHES_DIR.glob("**/clip_answers.json")):
            if '-prog' not in str(path): 
                continue
            seen += 1
            with open(path) as jf:
                data = json.load(jf)
            misc = data.get("data", {}).get(ANSWER_KEY)
            answer = misc.get("answer") if isinstance(misc, dict) else None
            if answer is None:
                missing += 1
                continue
            if isinstance(answer, str):
                salvaged_answer = salvage_answer(answer)
                if salvaged_answer is None:
                    invalid += 1
                    continue
                answer = salvaged_answer
                salvaged += 1
            elif not isinstance(answer, dict):
                invalid += 1
                continue
            second = data.get("data", {}).get(SECOND_PASS_KEY)
            second_answer = second.get("answer") if isinstance(second, dict) else None
            if isinstance(second_answer, str):
                second_answer = salvage_answer(second_answer)
            if not isinstance(second_answer, dict):
                second_answer = None
            writer.writerow(row_for(
                path,
                normalize_answer(answer),
                normalize_answer(second_answer) if second_answer else None,
            ))
            rows += 1
    print(f"written {rows} rows to {OUTPUT_PATH} ({missing} of {seen} files without {ANSWER_KEY}); {salvaged} salvaged, {invalid} invalid json")
    return ret


if __name__ == "__main__":
    raise SystemExit(main())
