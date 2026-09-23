"""Script created by opencode:e-research/arc:apex
Creates catalogue/predictions.csv from the misc1 answers found under
./batches/**/clip_answers.json: one row per answered clip, with the misc1
keys and values as columns alongside DODfilenameprefix and kdl_prog.
"""

from pathlib import Path
import ast
import csv
import json
import re

BATCHES_DIR = Path("batches")
OUTPUT_PATH = Path("catalogue") / "predictions-385.v2.csv"
ANSWER_KEY = "misc2"
DOD_PREFIX_COLUMN = "DODfilenameprefix"
KDL_PROG_COLUMN = "kdl_prog"
FIELDNAMES = [
    DOD_PREFIX_COLUMN,
    KDL_PROG_COLUMN,
    "title",
    "year",
    "place",
    "colour",
    "types",
    "fiction",
    "summary",
    "synopsis",
    "segments",
    "credits",
    "keywords",
]
# SYNOPSIS_KEY_VARIANTS = ("Synopsis", " synopsis", "summary")
LIST_SEPARATOR = "; "
SEGMENT_SEPARATOR = "; "
CREDIT_SEPARATOR = "; "
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


# def format_credits(credits) -> str:
#     """Credits as readable text: dict to 'key: value' pairs, list joined, str as-is."""
#     ret = format_value(credits)
#     if isinstance(credits, dict):
#         pairs = [f"{key}: {format_list(value)}" for key, value in credits.items()]
#         ret = CREDIT_SEPARATOR.join(pairs)
#     elif isinstance(credits, list):
#         ret = CREDIT_SEPARATOR.join(format_value(credit) for credit in credits)
#     return ret


def row_for(path: Path, answer: dict) -> dict:
    """One CSV row for a clip answer file: clip identity columns plus misc1 fields."""
    ret = {}
    for col in FIELDNAMES:
        ret[col] = format_value(answer.get(col, None), col)
    ret[DOD_PREFIX_COLUMN] = path.parent.parent.name.removesuffix(".32")
    ret[KDL_PROG_COLUMN] = "-".join(path.parent.name.split("-")[:2])

    return ret


def main() -> int:
    """Write catalogue/predictions.csv from the misc1 answers and report the outcome."""
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
            writer.writerow(row_for(path, normalize_answer(answer)))
            rows += 1
    print(f"written {rows} rows to {OUTPUT_PATH} ({missing} of {seen} files without {ANSWER_KEY}); {salvaged} salvaged, {invalid} invalid json")
    return ret


if __name__ == "__main__":
    raise SystemExit(main())
