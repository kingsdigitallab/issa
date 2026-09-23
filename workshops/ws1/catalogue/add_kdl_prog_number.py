"""Script created by opencode:e-research/arc:apex
Adds a kdl_prog_number column onto films-files.csv: the number of programmes
on the tape, derived per row as the count of discrete timecoded shotlist
entries, left blank where the row carries no such entries.
"""

from pathlib import Path
import re

import pandas as pd

CATALOGUE_DIR = Path(__file__).resolve().parent
FILMS_FILES_PATH = CATALOGUE_DIR / "films-files.csv"
SHOTLIST_COLUMN = "shotlist"
OUTPUT_COLUMN = "kdl_prog_number"
ENCODING = "cp1252"
TIMECODE_PATTERN = re.compile(r"\d{2}:\d{2}:\d{2}\t\d{2}:\d{2}:\d{2}")


def programme_count(shotlist):
    """Number of discrete timecoded shotlist entries in one row, '' if none."""
    ret = ""
    count = len(TIMECODE_PATTERN.findall(str(shotlist)))
    if count > 0:
        ret = str(count)
    return ret


def main():
    """Add kdl_prog_number to films-files.csv in place and report the outcome."""
    films_files = pd.read_csv(
        FILMS_FILES_PATH, encoding=ENCODING, dtype=str, na_filter=False
    )
    films_files[OUTPUT_COLUMN] = films_files[SHOTLIST_COLUMN].apply(programme_count)
    films_files.to_csv(FILMS_FILES_PATH, index=False, encoding=ENCODING)
    counted = (films_files[OUTPUT_COLUMN] != "").sum()
    print(
        f"written {len(films_files)} rows to {FILMS_FILES_PATH} "
        f"({counted} with {OUTPUT_COLUMN}, {len(films_files) - counted} blank)"
    )


if __name__ == "__main__":
    main()
