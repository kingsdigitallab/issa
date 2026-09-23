"""Script created by opencode:e-research/arc:apex
Adds DODfilenameprefix from Clips_Table.csv onto FILMS.csv, joining on `ref no`,
and writes the joined table to films-files.csv (prefix as the first column).
"""

from pathlib import Path

import pandas as pd

CATALOGUE_DIR = Path(__file__).resolve().parent
CLIPS_PATH = CATALOGUE_DIR / "Clips_Table.csv"
FILMS_PATH = CATALOGUE_DIR / "FILMS.csv"
OUTPUT_PATH = CATALOGUE_DIR / "films-files.csv"
JOIN_COLUMN = "ref no"
PREFIX_COLUMN = "DODfilenameprefix"
ENCODING = "cp1252"


def load_csv(path):
    """Read a catalogue CSV verbatim: every cell as a string, no NA coercion."""
    return pd.read_csv(path, encoding=ENCODING, dtype=str, na_filter=False)


def add_prefixes(films, clips):
    """Left-join DODfilenameprefix from clips onto films and move it to the front."""
    prefixes = clips[[PREFIX_COLUMN, JOIN_COLUMN]]
    ret = films.merge(prefixes, on=JOIN_COLUMN, how="left")
    ret = ret[[PREFIX_COLUMN] + list(films.columns)]
    return ret


def main():
    films = load_csv(FILMS_PATH)
    clips = load_csv(CLIPS_PATH)
    joined = add_prefixes(films, clips)
    joined.to_csv(OUTPUT_PATH, index=False, encoding=ENCODING)
    matched = (joined[PREFIX_COLUMN] != "").sum()
    print(f"written {len(joined)} rows to {OUTPUT_PATH} ({matched} with {PREFIX_COLUMN})")


if __name__ == "__main__":
    main()
