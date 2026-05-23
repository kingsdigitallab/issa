import csv
import shutil
import sys
from datetime import timedelta


def format_duration(seconds):
    return str(int(float(seconds)))


def main():
    cols = ["model_id", "seed", "video", "comparison_score", "comparison_summary", "duration_seconds", "comments"]
    out_headers = ["model", "seed", "video", "score", "summary", "duration", "comments"]

    rows = []
    with open("evaluations.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append([r[c] for c in cols])

    if not rows:
        print("No data found.")
        return

    col_widths = [len(h) for h in out_headers]
    for row in rows:
        row[5] = format_duration(row[5])
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    term_width = shutil.get_terminal_size().columns
    total_width = sum(col_widths) + 3 * (len(out_headers) - 1) + 4

    if total_width > term_width:
        max_summary = max(20, term_width - (total_width - col_widths[4]))
        col_widths[4] = max_summary
        for row in rows:
            s = str(row[4])
            if len(s) > max_summary:
                row[4] = s[:max_summary - 3] + "..."
            col_widths[4] = max(col_widths[4], len(row[4]))
        total_width = sum(col_widths) + 3 * (len(out_headers) - 1) + 4

    def sep():
        parts = ["─" * (w + 2) for w in col_widths]
        print("┌" + "┬".join(parts) + "┐")

    def line(cells):
        parts = []
        for i, c in enumerate(cells):
            pad = str(c).rjust(col_widths[i]) if i == 5 else str(c).ljust(col_widths[i])
            parts.append(f" {pad} ")
        print("│" + "│".join(parts) + "│")

    def mid_sep():
        parts = ["─" * (w + 2) for w in col_widths]
        print("├" + "┼".join(parts) + "┤")

    def bottom_sep():
        parts = ["─" * (w + 2) for w in col_widths]
        print("└" + "┴".join(parts) + "┘")

    sep()
    line(out_headers)
    mid_sep()
    for row in rows:
        line(row)
    bottom_sep()


if __name__ == "__main__":
    main()
