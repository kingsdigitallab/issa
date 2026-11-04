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
PROGRAMME_COLUMN = "programme"
BANDS_COLUMN = "bands"
ENVIRONMENT_COLUMN = "environment"
SECOND_PASS_COLUMNS = (PROGRAMME_COLUMN, BANDS_COLUMN, ENVIRONMENT_COLUMN)
PROGRAMME_TRUE = "true"
PROGRAMME_FALSE = "false"
STATUS_OK = "ok"
STATUS_SALVAGED = "salvaged"
STATUS_MISSING = "missing"
STATUS_INVALID = "invalid"
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


def extract_answer(data: dict, key: str) -> tuple[dict | None, str]:
    """Normalised answer dict and its status for a question key."""
    ret = (None, STATUS_MISSING)
    misc = data.get("data", {}).get(key)
    answer = misc.get("answer") if isinstance(misc, dict) else None
    if answer is None:
        return ret
    status = STATUS_OK
    if isinstance(answer, str):
        answer = salvage_answer(answer)
        status = STATUS_SALVAGED if answer is not None else STATUS_INVALID
    elif not isinstance(answer, dict):
        status = STATUS_INVALID
    if isinstance(answer, dict):
        ret = (normalize_answer(answer), status)
    else:
        ret = (None, status)
    return ret


def is_valid_value(column: str, value) -> bool:
    """True if a non-None value has the expected type for its answer column."""
    ret = True
    if column == PROGRAMME_COLUMN:
        ret = isinstance(value, bool) or (
            isinstance(value, str) and value.strip().lower() in (PROGRAMME_TRUE, PROGRAMME_FALSE)
        )
    elif column == BANDS_COLUMN:
        ret = isinstance(value, list)
    elif column == ENVIRONMENT_COLUMN:
        ret = isinstance(value, str)
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
    ret = {
        DOD_PREFIX_COLUMN: path.parent.parent.name.removesuffix(".32"),
        KDL_PROG_COLUMN: "-".join(path.parent.name.split("-")[:2]),
    }
    for col in FIELDNAMES:
        if col in ret:
            continue
        source = second_answer if col in SECOND_PASS_COLUMNS else answer
        value = source.get(col) if isinstance(source, dict) else None
        if value is None or not is_valid_value(col, value):
            ret[col] = NODATA
            continue
        if col == PROGRAMME_COLUMN:
            if isinstance(value, bool):
                value = str(value).lower()
            else:
                value = value.strip().lower()
        ret[col] = format_value(value, col)

    return ret


def main() -> int:
    """Write catalogue/predictions-400.v3.csv from the misc3 and secondpass1 answers and report the outcome."""
    ret = 0
    rows = 0
    seen = 0
    missing = 0
    salvaged = 0
    invalid = 0
    second_missing = 0
    second_salvaged = 0
    second_invalid = 0
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for path in sorted(BATCHES_DIR.glob("**/clip_answers.json")):
            if '-prog' not in str(path): 
                continue
            seen += 1
            with open(path) as jf:
                data = json.load(jf)
            answer, answer_status = extract_answer(data, ANSWER_KEY)
            if answer_status == STATUS_MISSING:
                missing += 1
            elif answer_status == STATUS_SALVAGED:
                salvaged += 1
            elif answer_status == STATUS_INVALID:
                invalid += 1
            second_answer, second_status = extract_answer(data, SECOND_PASS_KEY)
            if second_status == STATUS_MISSING:
                second_missing += 1
            elif second_status == STATUS_SALVAGED:
                second_salvaged += 1
            elif second_status == STATUS_INVALID:
                second_invalid += 1
            writer.writerow(row_for(path, answer or {}, second_answer))
            rows += 1
    print(f"written {rows} rows to {OUTPUT_PATH} ({missing} of {seen} files without {ANSWER_KEY}, {invalid} invalid; {second_missing} without {SECOND_PASS_KEY}, {second_invalid} invalid; {salvaged} + {second_salvaged} salvaged)")
    return ret


if __name__ == "__main__":
    raise SystemExit(main())
