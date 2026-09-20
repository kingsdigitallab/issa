"""Script created by opencode:e-research/arc:apex
Assesses catalogue/predictions.v2.csv against ground truth in an xlsx or ods
catalogue (metadata-16.xlsx by default, metadata-400.ods for the full run):
single films are compared field by field, compilation-tape clips are matched
to shotlist programme entries by timecode, a per-column quality report is
printed, and per-clip scores are written to catalogue/predictions.v2.eval.csv.
"""

from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
import argparse
import csv
import difflib
import re
import unicodedata
import zipfile

CATALOGUE_DIR = Path(__file__).resolve().parent
DEFAULT_PREDICTIONS_PATH = CATALOGUE_DIR / "predictions.v2.csv"
DEFAULT_METADATA_PATH = CATALOGUE_DIR / "metadata-16.xlsx"
DEFAULT_OUTPUT_PATH = CATALOGUE_DIR / "predictions.v2.eval.csv"
SHEET_NAME = "films-files"

XML_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
XML_REL_ATTR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
ODS_TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
ODS_TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
PROGRAMME_LINE_PATTERN = re.compile(r"^(\d{2}:\d{2}:\d{2})\t(\d{2}:\d{2}:\d{2})\t(\d{2}/\d{2}/\d{4})\t(.*)$")
MINUTE_TIMECODE_PATTERN = re.compile(r"\((\d+)\.(\d{2})\)")
PRED_SEGMENT_PATTERN = re.compile(r"^(?P<time>\d{1,2}:\d{2}(?::\d{2})?): (?P<title>.*)$")
YEAR_PATTERN = re.compile(r"\d{4}")
TOKEN_PATTERN = re.compile(r"[a-z0-9']+")

GT_DOD_COLUMN = "DODfilenameprefix"
GT_TITLE_COLUMN = "title"
GT_YEAR_COLUMN = "dateOfReleaseYYYY"
GT_TYPE_COLUMN = "type"
GT_FICTION_COLUMN = "Non-Fiction/ Fiction"
GT_COLOUR_COLUMN = "colour"
GT_CREDITS_COLUMNS = ("credits", "director/film-maker", "sponsor", "production co")
GT_SYNOPSIS_COLUMN = "synopsis"
GT_SHOTLIST_COLUMN = "shotlist"

PRED_DOD_COLUMN = "DODfilenameprefix"
PRED_KDL_COLUMN = "kdl_prog"
PRED_TITLE_COLUMN = "title"
PRED_YEAR_COLUMN = "year"
PRED_COLOUR_COLUMN = "colour"
PRED_TYPES_COLUMN = "types"
PRED_FICTION_COLUMN = "fiction"
PRED_SUMMARY_COLUMN = "summary"
PRED_SYNOPSIS_COLUMN = "synopsis"
PRED_SEGMENTS_COLUMN = "segments"
PRED_CREDITS_COLUMN = "credits"

EVAL_FIELDNAMES = (
    PRED_DOD_COLUMN,
    PRED_KDL_COLUMN,
    "cls",
    "title_pred",
    "title_ref",
    "title_exact",
    "title_ratio",
    "title_f1",
    "year_pred",
    "year_ref",
    "year_match",
    "colour_pred",
    "colour_ref",
    "colour_match",
    "fiction_pred",
    "fiction_ref",
    "fiction_match",
    "types_pred",
    "types_ref",
    "types_p",
    "types_r",
    "types_f1",
    "summary_f1",
    "summary_ratio",
    "synopsis_f1",
    "synopsis_ratio",
    "seg_time_p",
    "seg_time_r",
    "seg_pair_f1",
    "seg_title_r",
    "seg_second_chance",
    "seg_prog_windows",
    "seg_count_pred",
    "seg_count_ref",
    "credits_p",
    "credits_r",
)

COLOUR_MAP = {
    "black-and-white": "bw",
    "bw": "bw",
    "colour": "col",
    "color": "col",
    "col": "col",
    "sepia": "sepia",
    "colour-and-black-and-white": "bwcol",
    "color-and-black-and-white": "bwcol",
    "bwcol": "bwcol",
}
FICTION_MAP = {"yes": "fiction", "no": "non-fiction"}
TYPE_SYNONYMS = {"tv sports": "tv sport"}
KNOWN_TYPE_LABELS = (
    "tv news", "tv sport", "tv sports", "tv arts", "tv doc", "amateur",
    "documentary", "sponsored", "educational", "promotional", "advertising",
    "animation", "fiction", "drama", "comedy", "horror", "home movie",
    "instructional", "religion", "scientific", "local topical", "medical",
    "industrial", "expedition", "music", "sport", "topical", "travelogue",
    "cine mag", "dance",
)
MIN_LABEL_RESIDUE = 4
MAX_CELL_REPEATS = 100
MAX_MISSING_FILMS = 20
CREDIT_STOPWORDS = frozenset((
    "d", "pc", "sp", "by", "the", "and", "a", "an", "of", "in", "for",
    "presents", "presented", "present", "production", "produced", "producer",
    "director", "writer", "filmed", "film", "maker", "co", "ltd",
))
LEXICAL_STOPWORDS = frozenset((
    "the", "a", "an", "of", "in", "and", "to", "is", "are", "with", "on",
    "at", "for", "by", "from", "int", "ext", "gvs", "cu", "ls",
))
TITLE_STRIP_CHARS = "()[]'\".,"
NEAREST_TOLERANCE_S = 30
SEGMENT_TOLERANCE_S = 30
ROUND_DIGITS = 3
MAX_EXAMPLES = 8


def match_known_labels(text):
    """Canonical labels found in a type value by greedy longest match."""
    ret = []
    compact_to_label = {}
    for label in KNOWN_TYPE_LABELS:
        compact = re.sub(r"[^a-z0-9]", "", label)
        compact_to_label[compact] = label
    known = sorted(compact_to_label, key=len, reverse=True)
    compact = re.sub(r"[^a-z0-9]", "", fold_ascii(text))
    residue = ""
    while compact:
        matched = ""
        for candidate in known:
            if compact.startswith(candidate):
                matched = candidate
                break
        if matched:
            if len(residue) >= MIN_LABEL_RESIDUE:
                ret.append(residue)
            residue = ""
            ret.append(compact_to_label[matched])
            compact = compact[len(matched):]
        else:
            residue += compact[0]
            compact = compact[1:]
    if len(residue) >= MIN_LABEL_RESIDUE:
        ret.append(residue)
    return ret


def parse_type_labels(value):
    """A GT or predicted type cell as a set of labels, splitting concatenations."""
    ret = set()
    for part in re.split(r"[,\n;]", value.casefold()):
        ret.update(match_known_labels(part))
    return ret


def column_number(cell_ref):
    """1-based column number of an xlsx cell reference such as 'AB12'."""
    ret = 0
    for ch in re.match(r"[A-Z]+", cell_ref).group():
        ret = ret * 26 + ord(ch) - 64
    return ret


def fold_ascii(text):
    """Text with accents and non-ascii characters folded away, casefolded."""
    ret = unicodedata.normalize("NFKD", text.casefold()).encode("ascii", "ignore").decode()
    return ret


def read_shared_strings(archive):
    """Shared-string table of an xlsx archive as a list of strings."""
    ret = []
    if "xl/sharedStrings.xml" in archive.namelist():
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        for si in root.iter(f"{{{XML_MAIN_NS}}}si"):
            ret.append("".join(t.text or "" for t in si.iter(f"{{{XML_MAIN_NS}}}t")))
    return ret


def cell_text(cell, shared_strings):
    """Cell value as a string: shared or inline string, or the raw value."""
    ret = ""
    if cell.get("t") == "s":
        value = cell.find(f"{{{XML_MAIN_NS}}}v")
        if value is not None and value.text is not None:
            ret = shared_strings[int(value.text)]
    elif cell.get("t") == "inlineStr":
        text = cell.find(f"{{{XML_MAIN_NS}}}is/{{{XML_MAIN_NS}}}t")
        if text is not None:
            ret = text.text or ""
    else:
        value = cell.find(f"{{{XML_MAIN_NS}}}v")
        if value is not None:
            ret = value.text or ""
    return ret


def read_xlsx_sheet(path, sheet_name):
    """Rows of the named xlsx sheet as dicts keyed by the header row."""
    ret = []
    with zipfile.ZipFile(path) as archive:
        shared_strings = read_shared_strings(archive)
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = {
            rel.get("Id"): rel.get("Target")
            for rel in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        }
        target = None
        for sheet in workbook.iter(f"{{{XML_MAIN_NS}}}sheet"):
            if sheet.get("name") == sheet_name:
                target = rels.get(sheet.get(XML_REL_ATTR))
        if target is None:
            raise SystemExit(f"sheet {sheet_name!r} not found in {path}")
        if not target.startswith("xl/"):
            target = "xl/" + target
        worksheet = ET.fromstring(archive.read(target))
    rows = []
    for row in worksheet.iter(f"{{{XML_MAIN_NS}}}row"):
        values = {}
        for cell in row.iter(f"{{{XML_MAIN_NS}}}c"):
            values[column_number(cell.get("r"))] = cell_text(cell, shared_strings)
        rows.append(values)
    header = [rows[0].get(i, "") for i in range(1, max(rows[0]) + 1)]
    for values in rows[1:]:
        ret.append({name: values.get(i, "") for i, name in enumerate(header, start=1) if name})
    return ret


def ods_cell_text(cell):
    """Text of an ods cell with tabs, repeated spaces and line breaks preserved."""
    paragraphs = []
    for paragraph in cell.iter(f"{{{ODS_TEXT_NS}}}p"):
        chunks = []
        for elem in paragraph.iter():
            if elem.tag == f"{{{ODS_TEXT_NS}}}s":
                chunks.append(" " * int(elem.get(f"{{{ODS_TEXT_NS}}}c", "1")))
            elif elem.tag == f"{{{ODS_TEXT_NS}}}tab":
                chunks.append("\t")
            elif elem.tag == f"{{{ODS_TEXT_NS}}}line-break":
                chunks.append("\n")
            elif elem.text:
                chunks.append(elem.text)
            if elem.tail:
                chunks.append(elem.tail)
        paragraphs.append("".join(chunks))
    ret = "\n".join(paragraphs)
    return ret


def read_ods_sheet(path, sheet_name):
    """Rows of the named ods sheet as dicts keyed by the header row."""
    ret = []
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    table = next(
        (t for t in root.iter(f"{{{ODS_TABLE_NS}}}table") if t.get(f"{{{ODS_TABLE_NS}}}name") == sheet_name),
        None,
    )
    if table is None:
        raise SystemExit(f"sheet {sheet_name!r} not found in {path}")
    rows = []
    for row in table.iter(f"{{{ODS_TABLE_NS}}}table-row"):
        values = []
        for cell in row.iter(f"{{{ODS_TABLE_NS}}}table-cell"):
            repeats = int(cell.get(f"{{{ODS_TABLE_NS}}}number-columns-repeated", "1"))
            values.extend([ods_cell_text(cell)] * min(repeats, MAX_CELL_REPEATS))
        rows.append(values)
    header = rows[0]
    for values in rows[1:]:
        ret.append({name: values[i] if i < len(values) else "" for i, name in enumerate(header) if name})
    return ret


def read_sheet(path, sheet_name):
    """Rows of the named xlsx or ods sheet as dicts keyed by the header row."""
    if str(path).endswith(".ods"):
        ret = read_ods_sheet(path, sheet_name)
    else:
        ret = read_xlsx_sheet(path, sheet_name)
    return ret


def to_secs(hms):
    """'HH:MM:SS' or 'MM:SS' timecode as integer seconds."""
    ret = 0
    parts = [int(part) for part in hms.split(":")]
    if len(parts) == 3:
        ret = parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        ret = parts[0] * 60 + parts[1]
    return ret


def clip_start_secs(kdl_prog):
    """Tape offset in seconds of a clip id such as '00.44.10-338'."""
    ret = to_secs(kdl_prog.split("-")[0].replace(".", ":"))
    return ret


def parse_programmes(shotlist):
    """(start_secs, end_secs, tx_date, title) tuples of timecoded tape programmes."""
    ret = []
    lines = shotlist.splitlines()
    i = 0
    while i < len(lines):
        match = PROGRAMME_LINE_PATTERN.match(lines[i])
        if match:
            title = match.group(4).strip()
            if not title:
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines):
                    title = lines[j].strip()
                    i = j
            ret.append((to_secs(match.group(1)), to_secs(match.group(2)), match.group(3), title))
        i += 1
    return ret


def match_programme(programmes, start_secs):
    """Programme whose start is nearest the clip start, None beyond tolerance."""
    ret = None
    best_distance = None
    for programme in programmes:
        distance = abs(programme[0] - start_secs)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            ret = programme
    if best_distance is None or best_distance > NEAREST_TOLERANCE_S:
        ret = None
    return ret


def parse_shotlist_timecodes(shotlist):
    """(secs, text) pairs of '(M.SS)' timecoded chunks in a shotlist."""
    ret = []
    matches = list(MINUTE_TIMECODE_PATTERN.finditer(shotlist))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(shotlist)
        text = shotlist[match.end():end]
        ret.append((int(match.group(1)) * 60 + int(match.group(2)), text))
    return ret


def parse_pred_segments(value):
    """(secs, title) pairs of a predictions 'segments' cell."""
    ret = []
    if value:
        for entry in value.split("; "):
            match = PRED_SEGMENT_PATTERN.match(entry.strip())
            if match:
                ret.append((to_secs(match.group("time")), match.group("title").strip()))
    return ret


def normalize_title(text):
    """Title ready for exact comparison: casefolded, brackets and punctuation removed."""
    stripped = "".join(ch for ch in text if ch not in TITLE_STRIP_CHARS)
    ret = " ".join(fold_ascii(stripped).split())
    return ret


def normalize_text(text):
    """Casefolded ascii text with whitespace collapsed, for ratio comparisons."""
    ret = " ".join(fold_ascii(text).split())
    return ret


def tokens(text):
    """Casefolded word tokens of a text, without wrapping apostrophes."""
    ret = [token.strip("'") for token in TOKEN_PATTERN.findall(fold_ascii(text))]
    ret = [token for token in ret if token]
    return ret


def content_tokens(text):
    """Word tokens of a text without stopwords."""
    ret = [token for token in tokens(text) if token not in LEXICAL_STOPWORDS]
    return ret


def rounded(value):
    """Value rounded to the report precision."""
    ret = round(value, ROUND_DIGITS)
    return ret


def text_ratio(pred_text, ref_text):
    """difflib similarity ratio of two normalized texts."""
    ret = difflib.SequenceMatcher(None, normalize_text(pred_text), normalize_text(ref_text)).ratio()
    return ret


def rouge1(pred_text, ref_text):
    """(precision, recall, f1) of ROUGE-1 token overlap between two texts."""
    ret = (None, None, None)
    pred_counts = Counter(tokens(pred_text))
    ref_counts = Counter(tokens(ref_text))
    overlap = sum((pred_counts & ref_counts).values())
    n_pred = sum(pred_counts.values())
    n_ref = sum(ref_counts.values())
    if n_pred and n_ref:
        precision = overlap / n_pred
        recall = overlap / n_ref
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        ret = (precision, recall, f1)
    return ret


def content_recall(pred_text, ref_text):
    """Recall of a reference text's content tokens within a prediction."""
    ret = None
    pred_set = set(content_tokens(pred_text))
    ref_list = content_tokens(ref_text)
    if ref_list:
        ret = sum(1 for token in ref_list if token in pred_set) / len(ref_list)
    return ret


def set_prf(pred_set, ref_set):
    """(precision, recall, f1) of two label sets, all None when both empty."""
    ret = (None, None, None)
    if pred_set or ref_set:
        precision = len(pred_set & ref_set) / len(pred_set) if pred_set else 0.0
        recall = len(pred_set & ref_set) / len(ref_set) if ref_set else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        ret = (precision, recall, f1)
    return ret


def pred_type_set(value):
    """A predicted types cell as a set of mapped labels."""
    ret = set()
    for label in parse_type_labels(value):
        ret.add(TYPE_SYNONYMS.get(label, label))
    return ret


def credit_tokens(text):
    """Significant name tokens of a credits text."""
    ret = set()
    for token in tokens(text):
        if token not in CREDIT_STOPWORDS and len(token) > 1:
            ret.add(token)
    return ret


def time_prf(pred_times, ref_times, tolerance):
    """(precision, recall) of two timecode lists matched within a tolerance."""
    matched = [False] * len(ref_times)
    hits = 0
    for pred_time in pred_times:
        for i, ref_time in enumerate(ref_times):
            if not matched[i] and abs(ref_time - pred_time) <= tolerance:
                matched[i] = True
                hits += 1
                break
    precision = hits / len(pred_times) if pred_times else None
    recall = hits / len(ref_times) if ref_times else None
    ret = (precision, recall)
    return ret


def matched_pair_f1(pred_segs, ref_segs, offset, tolerance):
    """Mean ROUGE-1 F1 over pred/ref segment pairs matched within a time tolerance."""
    f1s = []
    used = [False] * len(ref_segs)
    for pred_time, pred_title in pred_segs:
        for i, (ref_time, _) in enumerate(ref_segs):
            if not used[i] and abs((offset + pred_time) - ref_time) <= tolerance:
                used[i] = True
                _, _, f1 = rouge1(pred_title, ref_segs[i][1])
                if f1 is not None:
                    f1s.append(f1)
                break
    ret = sum(f1s) / len(f1s) if f1s else None
    return ret


def tx_year(programme):
    """Broadcast year of a matched programme entry, '' if unknown."""
    ret = ""
    if programme:
        match = YEAR_PATTERN.search(programme[2])
        if match:
            ret = match.group()
    return ret


def film_context(gt_row):
    """Per-film ground-truth context: tape fields plus shotlist-derived data."""
    shotlist = gt_row.get(GT_SHOTLIST_COLUMN, "")
    programmes = parse_programmes(shotlist)
    ret = {
        "dod": gt_row.get(GT_DOD_COLUMN, ""),
        "title": gt_row.get(GT_TITLE_COLUMN, ""),
        "year": gt_row.get(GT_YEAR_COLUMN, ""),
        "types": parse_type_labels(gt_row.get(GT_TYPE_COLUMN, "")),
        "fiction": gt_row.get(GT_FICTION_COLUMN, "").strip().casefold(),
        "colour": gt_row.get(GT_COLOUR_COLUMN, "").strip().casefold(),
        "credits_text": " ".join(gt_row.get(column, "") for column in GT_CREDITS_COLUMNS),
        "synopsis": gt_row.get(GT_SYNOPSIS_COLUMN, ""),
        "shotlist_timecodes": parse_shotlist_timecodes(shotlist),
        "programmes": programmes,
        "is_compilation": bool(programmes),
    }
    return ret


def annotate_clip_starts(contexts, preds):
    """Add per-film clip start times and separator-missed programme starts to contexts."""
    starts_by_film = {}
    for pred in preds:
        starts_by_film.setdefault(pred[PRED_DOD_COLUMN], []).append(clip_start_secs(pred[PRED_KDL_COLUMN]))
    for dod, ctx in contexts.items():
        clip_starts = starts_by_film.get(dod, [])
        ctx["clip_starts"] = clip_starts
        ctx["missed_starts"] = [
            programme[0]
            for programme in ctx["programmes"]
            if not any(abs(start - programme[0]) <= NEAREST_TOLERANCE_S for start in clip_starts)
        ]


def eval_clip(pred, ctx):
    """One per-clip evaluation record against its film's ground truth."""
    ret = {name: "" for name in EVAL_FIELDNAMES}
    is_compilation = ctx["is_compilation"]
    start = clip_start_secs(pred[PRED_KDL_COLUMN])
    programme = match_programme(ctx["programmes"], start) if is_compilation else None
    ret["cls"] = "B" if is_compilation else "A"
    ret[PRED_DOD_COLUMN] = pred[PRED_DOD_COLUMN]
    ret[PRED_KDL_COLUMN] = pred[PRED_KDL_COLUMN]

    ref_title = programme[3] if programme else ("" if is_compilation else ctx["title"])
    ret["title_pred"] = pred[PRED_TITLE_COLUMN]
    ret["title_ref"] = ref_title
    if ref_title:
        ret["title_exact"] = int(normalize_title(pred[PRED_TITLE_COLUMN]) == normalize_title(ref_title))
        ret["title_ratio"] = rounded(text_ratio(pred[PRED_TITLE_COLUMN], ref_title))
        _, _, ret["title_f1"] = rouge1(pred[PRED_TITLE_COLUMN], ref_title)
        if ret["title_f1"] is not None:
            ret["title_f1"] = rounded(ret["title_f1"])

    if is_compilation:
        ref_year = tx_year(programme) or ctx["year"]
    else:
        ref_year = ctx["year"]
    match = YEAR_PATTERN.search(pred[PRED_YEAR_COLUMN])
    pred_year = match.group() if match else ""
    ret["year_pred"] = pred_year
    ret["year_ref"] = ref_year
    if pred_year and ref_year:
        ret["year_match"] = int(int(pred_year) == int(ref_year))

    colour_pred = COLOUR_MAP.get(pred[PRED_COLOUR_COLUMN].strip().casefold(), "")
    colour_ref = COLOUR_MAP.get(ctx["colour"], ctx["colour"])
    ret["colour_pred"] = colour_pred
    ret["colour_ref"] = colour_ref
    if colour_pred and colour_ref:
        ret["colour_match"] = int(colour_pred == colour_ref)

    fiction_pred = FICTION_MAP.get(pred[PRED_FICTION_COLUMN].strip().casefold(), "")
    ret["fiction_pred"] = fiction_pred
    ret["fiction_ref"] = ctx["fiction"]
    if fiction_pred and ctx["fiction"]:
        ret["fiction_match"] = int(fiction_pred == ctx["fiction"])

    pred_types = pred_type_set(pred[PRED_TYPES_COLUMN])
    ref_types = ctx["types"]
    ret["types_pred"] = "; ".join(sorted(pred_types))
    ret["types_ref"] = "; ".join(sorted(ref_types))
    types_p, types_r, types_f1 = set_prf(pred_types, ref_types)
    if types_p is not None:
        ret["types_p"] = rounded(types_p)
        ret["types_r"] = rounded(types_r)
        ret["types_f1"] = rounded(types_f1)

    if not is_compilation:
        for source, prefix in ((PRED_SUMMARY_COLUMN, "summary"), (PRED_SYNOPSIS_COLUMN, "synopsis")):
            if pred[source] and ctx["synopsis"]:
                _, _, f1 = rouge1(pred[source], ctx["synopsis"])
                if f1 is not None:
                    ret[f"{prefix}_f1"] = rounded(f1)
                ret[f"{prefix}_ratio"] = rounded(text_ratio(pred[source], ctx["synopsis"]))

    pred_segs = parse_pred_segments(pred[PRED_SEGMENTS_COLUMN])
    ret["seg_count_pred"] = len(pred_segs)
    if is_compilation:
        ret["seg_count_ref"] = 1 if programme else 0
        if ctx["missed_starts"] and pred_segs:
            ret["seg_second_chance"] = int(
                any(
                    abs(start + seg_time - missed) <= NEAREST_TOLERANCE_S
                    for seg_time, _ in pred_segs
                    for missed in ctx["missed_starts"]
                )
            )
        windows = set()
        recalls = []
        for seg_time, seg_title in pred_segs:
            abs_time = start + seg_time
            window = next((p for p in ctx["programmes"] if p[0] <= abs_time < p[1]), None)
            if window is None:
                continue
            windows.add(window[0])
            recall = content_recall(seg_title, window[3])
            if recall is not None:
                recalls.append(recall)
        if windows:
            ret["seg_prog_windows"] = len(windows)
        if recalls:
            ret["seg_title_r"] = rounded(sum(recalls) / len(recalls))
    else:
        ref_segs = ctx["shotlist_timecodes"]
        ret["seg_count_ref"] = len(ref_segs)
        seg_p, seg_r = time_prf(
            [start + time for time, _ in pred_segs],
            [time for time, _ in ref_segs],
            SEGMENT_TOLERANCE_S,
        )
        if seg_p is not None:
            ret["seg_time_p"] = rounded(seg_p)
        if seg_r is not None:
            ret["seg_time_r"] = rounded(seg_r)
        pair_f1 = matched_pair_f1(pred_segs, ref_segs, start, SEGMENT_TOLERANCE_S)
        if pair_f1 is not None:
            ret["seg_pair_f1"] = rounded(pair_f1)

    pred_credit_tokens = credit_tokens(pred[PRED_CREDITS_COLUMN])
    ref_credit_tokens = credit_tokens(ctx["credits_text"])
    if pred_credit_tokens and ref_credit_tokens:
        overlap = pred_credit_tokens & ref_credit_tokens
        ret["credits_p"] = rounded(len(overlap) / len(pred_credit_tokens))
        ret["credits_r"] = rounded(len(overlap) / len(ref_credit_tokens))

    return ret


def fmt(value):
    """Formatted number for the report, 'n/a' when missing."""
    ret = "n/a" if value in (None, "") else f"{value:.3f}".rstrip("0").rstrip(".")
    return ret


def mean_field(rows, field):
    """Mean of a numeric field over rows, ignoring blank values."""
    values = [row[field] for row in rows if row[field] not in ("", None)]
    ret = sum(values) / len(values) if values else None
    return ret


def count_true(rows, field):
    """Number of rows whose field is set to 1."""
    ret = sum(1 for row in rows if row[field] == 1)
    return ret


def report_title(rows_a, rows_b):
    print("-- title --")
    for label, rows in (("A", rows_a), ("B", rows_b)):
        exact = count_true(rows, "title_exact")
        scored = [row for row in rows if row["title_exact"] != ""]
        empty = sum(1 for row in rows if not row["title_pred"])
        suffix = f", empty predicted titles: {empty}/{len(rows)}" if empty else ""
        print(
            f"  {label}: exact {exact}/{len(scored)}, mean ratio "
            f"{fmt(mean_field(rows, 'title_ratio'))}, mean token-F1 "
            f"{fmt(mean_field(rows, 'title_f1'))}{suffix}"
        )
    for row in rows_a:
        if row["title_exact"] == 0:
            print(f"    miss {row[PRED_DOD_COLUMN]}: {row['title_pred']!r} vs GT {row['title_ref']!r}")
    misses = [row for row in rows_b if row["title_exact"] == 0]
    for row in misses[:MAX_EXAMPLES]:
        print(f"    miss {row[PRED_DOD_COLUMN]} {row[PRED_KDL_COLUMN]}: {row['title_pred']!r} vs GT {row['title_ref'][:60]!r}")
    if len(misses) > MAX_EXAMPLES:
        print(f"    ... and {len(misses) - MAX_EXAMPLES} more")


def report_year(rows_a, rows_b):
    print("-- year --")
    for label, rows in (("A", rows_a), ("B", rows_b)):
        predicted = [row for row in rows if row["year_pred"]]
        correct = count_true(predicted, "year_match")
        print(f"  {label}: predicted {len(predicted)}/{len(rows)}, correct {correct}/{len(predicted)}")
        for row in predicted:
            if row["year_match"] == 0:
                print(f"    miss {row[PRED_DOD_COLUMN]} {row[PRED_KDL_COLUMN]}: {row['year_pred']} vs GT {row['year_ref']}")


def report_colour(rows_a, rows_b):
    print("-- colour --")
    for label, rows in (("A", rows_a), ("B", rows_b)):
        scored = [row for row in rows if row["colour_match"] != ""]
        matches = count_true(scored, "colour_match")
        print(f"  {label}: {matches}/{len(scored)} correct")
        misses = [row for row in scored if row["colour_match"] == 0]
        for row in misses[:MAX_EXAMPLES]:
            print(f"    miss {row[PRED_DOD_COLUMN]} {row[PRED_KDL_COLUMN]}: {row['colour_pred']} vs GT {row['colour_ref']}")
        if len(misses) > MAX_EXAMPLES:
            print(f"    ... and {len(misses) - MAX_EXAMPLES} more")
    print("  (class B reference is tape-level colour; genuinely B/W items on a colour tape count as misses)")


def report_fiction(rows_a, rows_b):
    print("-- fiction --")
    for label, rows in (("A", rows_a), ("B", rows_b)):
        scored = [row for row in rows if row["fiction_match"] != ""]
        skipped = len(rows) - len(scored)
        matches = count_true(scored, "fiction_match")
        suffix = f", {skipped} skipped (no prediction or no GT)" if skipped else ""
        print(f"  {label}: {matches}/{len(scored)} correct{suffix}")
        for row in scored:
            if row["fiction_match"] == 0:
                print(f"    miss {row[PRED_DOD_COLUMN]} {row[PRED_KDL_COLUMN]}: {row['fiction_pred']} vs GT {row['fiction_ref']}")


def micro_types(rows):
    """(precision, recall, f1) of label sets micro-aggregated over rows."""
    inter = 0
    n_pred = 0
    n_ref = 0
    for row in rows:
        pred_set = set(filter(None, row["types_pred"].split("; ")))
        ref_set = set(filter(None, row["types_ref"].split("; ")))
        inter += len(pred_set & ref_set)
        n_pred += len(pred_set)
        n_ref += len(ref_set)
    precision = inter / n_pred if n_pred else None
    recall = inter / n_ref if n_ref else None
    f1 = None
    if precision is not None and recall is not None and precision + recall:
        f1 = 2 * precision * recall / (precision + recall)
    ret = (precision, recall, f1)
    return ret


def label_drift(rows, direction):
    """Counter summary of type labels unconfirmed in one direction, formatted."""
    counts = Counter()
    for row in rows:
        pred_set = set(filter(None, row["types_pred"].split("; ")))
        ref_set = set(filter(None, row["types_ref"].split("; ")))
        counts.update((pred_set - ref_set) if direction == "pred" else (ref_set - pred_set))
    ret = ", ".join(f"{label}({count})" for label, count in counts.most_common())
    return ret


def report_types(rows_a, rows_b):
    print("-- types --")
    for label, rows in (("A", rows_a), ("B", rows_b)):
        precision, recall, f1 = micro_types(rows)
        print(f"  {label}: mapped micro P/R/F1 {fmt(precision)} / {fmt(recall)} / {fmt(f1)}")
        drift = label_drift(rows, "pred")
        if drift:
            print(f"    predicted but not in GT: {drift}")
        missed = label_drift(rows, "ref")
        if missed:
            print(f"    in GT but not predicted: {missed}")


def report_text(rows_a, field):
    print(f"-- {field} --")
    scored = [row for row in rows_a if row[f"{field}_f1"] != ""]
    print(
        f"  A vs GT synopsis: mean ROUGE-1 F1 {fmt(mean_field(scored, f'{field}_f1'))}, "
        f"mean ratio {fmt(mean_field(scored, f'{field}_ratio'))} over {len(scored)}/{len(rows_a)} clips"
    )
    print("  B: n/a (no per-programme ground-truth text)")


def report_segments(rows_a, rows_b, contexts, preds):
    print("-- segments --")
    print(
        "  A: predicted chapters vs shot-level GT (cross-level): mean time-P "
        f"{fmt(mean_field(rows_a, 'seg_time_p'))} (boundaries real), shot-code coverage "
        f"{fmt(mean_field(rows_a, 'seg_time_r'))} (informational), matched-pair token-F1 "
        f"{fmt(mean_field(rows_a, 'seg_pair_f1'))}; mean counts pred "
        f"{fmt(mean_field(rows_a, 'seg_count_pred'))} vs GT {fmt(mean_field(rows_a, 'seg_count_ref'))}"
    )
    for row in rows_a:
        print(
            f"    {row[PRED_DOD_COLUMN]}: {row['seg_count_pred']} chapters vs "
            f"{row['seg_count_ref']} GT codes (time-P {fmt(row['seg_time_p'])})"
        )
    tape_dods = sorted({row[PRED_DOD_COLUMN] for row in rows_b})
    total = clip_covered = seg_caught = 0
    uncovered = []
    tape_lines = []
    for dod in tape_dods:
        ctx = contexts[dod]
        all_seg_times = [
            clip_start_secs(p[PRED_KDL_COLUMN]) + time
            for p in preds
            if p[PRED_DOD_COLUMN] == dod
            for time, _ in parse_pred_segments(p[PRED_SEGMENTS_COLUMN])
        ]
        tape_total = len(ctx["programmes"])
        tape_clip = tape_seg = 0
        for programme in ctx["programmes"]:
            if any(abs(start - programme[0]) <= NEAREST_TOLERANCE_S for start in ctx["clip_starts"]):
                tape_clip += 1
            elif any(abs(time - programme[0]) <= NEAREST_TOLERANCE_S for time in all_seg_times):
                tape_seg += 1
            else:
                uncovered.append(f"{dod} @{programme[0]}s {programme[3][:48]!r}")
        total += tape_total
        clip_covered += tape_clip
        seg_caught += tape_seg
        tape_lines.append(f"    {dod}: {tape_clip}/{tape_total} by clip starts, +{tape_seg} by segments")
    if total:
        print(
            f"  B: GT programme starts covered {clip_covered}/{total} ({fmt(clip_covered / total)}) "
            f"by clip starts, +{seg_caught} by inner segments = "
            f"{clip_covered + seg_caught}/{total} ({fmt((clip_covered + seg_caught) / total)})"
        )
        for line in tape_lines:
            print(line)
        for entry in uncovered[:MAX_EXAMPLES]:
            print(f"    not covered: {entry}")
    multi = sum(
        1
        for row in rows_b
        if row["seg_prog_windows"] not in ("", None) and int(row["seg_prog_windows"]) > 1
    )
    print(
        f"  B: mean per-segment title recall {fmt(mean_field(rows_b, 'seg_title_r'))}; "
        f"clips whose segments span multiple GT programmes: {multi}/{len(rows_b)}"
    )


def report_credits(rows_a, rows_b):
    print("-- credits --")
    for label, rows in (("A", rows_a), ("B", rows_b)):
        scored = [row for row in rows if row["credits_p"] != ""]
        print(
            f"  {label}: token P {fmt(mean_field(scored, 'credits_p'))}, R "
            f"{fmt(mean_field(scored, 'credits_r'))} over {len(scored)}/{len(rows)} clips with GT credits"
        )


def print_report(eval_rows, contexts, preds, predictions_path, metadata_path, output_path):
    """Per-column quality report of the evaluation rows."""
    rows_a = [row for row in eval_rows if row["cls"] == "A"]
    rows_b = [row for row in eval_rows if row["cls"] == "B"]
    films = {row[PRED_DOD_COLUMN] for row in eval_rows}
    missing_films = sorted(set(contexts) - films)
    if len(missing_films) > MAX_MISSING_FILMS:
        missing_suffix = f" ({len(missing_films)} GT films without predictions)"
    elif missing_films:
        missing_suffix = f" (GT films without predictions: {', '.join(missing_films)})"
    else:
        missing_suffix = ")"
    print(
        f"predictions {predictions_path.name} vs {metadata_path.name}: {len(eval_rows)} clips "
        f"over {len(films)}/{len(contexts)} GT films{missing_suffix}"
    )
    print(f"class A single films: {len(rows_a)} clips | class B compilation tapes: {len(rows_b)} clips\n")

    report_title(rows_a, rows_b)
    report_year(rows_a, rows_b)
    report_colour(rows_a, rows_b)
    report_fiction(rows_a, rows_b)
    report_types(rows_a, rows_b)
    report_text(rows_a, "summary")
    report_text(rows_a, "synopsis")
    report_segments(rows_a, rows_b, contexts, preds)
    report_credits(rows_a, rows_b)
    print("-- place --")
    print("  N/A: no ground-truth column in the catalogue")
    print("-- keywords --")
    print("  N/A: no ground-truth column in the catalogue")
    print(f"\nper-clip scores written to {output_path}")


def main() -> int:
    """Evaluate predictions against ground truth and report per-column quality."""
    ret = 0
    parser = argparse.ArgumentParser(
        description="Assess predictions.csv against xlsx/ods ground truth"
    )
    parser.add_argument(
        "--gt",
        type=Path,
        default=DEFAULT_METADATA_PATH,
        help=f"ground-truth xlsx or ods catalogue (default: {DEFAULT_METADATA_PATH})",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=DEFAULT_PREDICTIONS_PATH,
        help=f"predictions CSV (default: {DEFAULT_PREDICTIONS_PATH})",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"per-clip score CSV to write (default: {DEFAULT_OUTPUT_PATH})",
    )
    args = parser.parse_args()

    contexts = {
        row[GT_DOD_COLUMN]: film_context(row)
        for row in read_sheet(args.gt, SHEET_NAME)
        if row.get(GT_DOD_COLUMN)
    }
    with open(args.predictions, newline="") as f:
        preds = list(csv.DictReader(f))
    annotate_clip_starts(contexts, preds)
    unknown = [pred for pred in preds if pred[PRED_DOD_COLUMN] not in contexts]
    if unknown:
        print(f"skipping {len(unknown)} clips without a GT film row")
    eval_rows = [eval_clip(pred, contexts[pred[PRED_DOD_COLUMN]]) for pred in preds if pred not in unknown]
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EVAL_FIELDNAMES)
        writer.writeheader()
        writer.writerows(eval_rows)
    print_report(eval_rows, contexts, preds, args.predictions, args.gt, args.out)
    return ret


if __name__ == "__main__":
    raise SystemExit(main())
