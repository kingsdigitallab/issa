'''
Display on terminal a human-readable version of evaluations.csv.
Also shows show average performances per model.

Authors: opencoder:kimi-k2.6
Prompts & tweaks: GN
'''

import csv
import shutil


def format_duration(seconds):
    return str(int(float(seconds)))


def draw_table(headers, rows, align):
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    def sep(left, mid, right):
        parts = ["─" * (w + 2) for w in col_widths]
        print(left + mid.join(parts) + right)

    def line(cells):
        parts = []
        for i, c in enumerate(cells):
            pad = str(c).rjust(col_widths[i]) if align[i] == 'r' else str(c).ljust(col_widths[i])
            parts.append(f" {pad} ")
        print("│" + "│".join(parts) + "│")

    sep("┌", "┬", "┐")
    line(headers)
    sep("├", "┼", "┤")
    for row in rows:
        line(row)
    sep("└", "┴", "┘")


def main():
    cols = ["model_id", "seed", "video", "comparison_score", "comparison_summary", "duration_seconds", "comments"]

    raw_rows = []
    with open("evaluations.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            raw_rows.append([r[c] for c in cols])

    if not raw_rows:
        print("No data found.")
        return

    detail_headers = ["model", "seed", "video", "score", "summary", "duration", "comments"]
    detail_align = ['l', 'l', 'l', 'r', 'l', 'r', 'l']
    detail_rows = []
    for row in raw_rows:
        detail_rows.append([
            row[0],
            row[1],
            row[2],
            str(int(float(row[3]) * 100)),
            row[4],
            format_duration(row[5]),
            row[6],
        ])

    term_width = shutil.get_terminal_size().columns
    detail_widths = [len(h) for h in detail_headers]
    for row in detail_rows:
        for i, cell in enumerate(row):
            detail_widths[i] = max(detail_widths[i], len(str(cell)))
    total_width = sum(detail_widths) + 3 * (len(detail_headers) - 1) + 4
    if total_width > term_width:
        max_summary = max(20, term_width - (total_width - detail_widths[4]))
        detail_widths[4] = max_summary
        for row in detail_rows:
            s = str(row[4])
            if len(s) > max_summary:
                row[4] = s[:max_summary - 3] + "..."
            detail_widths[4] = max(detail_widths[4], len(row[4]))

    draw_table(detail_headers, detail_rows, detail_align)

    blocks = []
    current_model = raw_rows[0][0]
    current_comments = raw_rows[0][6]
    block_scores = [float(raw_rows[0][3])]
    block_durations = [float(raw_rows[0][5])]

    for row in raw_rows[1:]:
        if row[0] == current_model and row[6] == current_comments:
            block_scores.append(float(row[3]))
            block_durations.append(float(row[5]))
        else:
            avg_score = sum(block_scores) / len(block_scores)
            avg_duration = sum(block_durations) / len(block_durations)
            blocks.append([
                current_model,
                current_comments,
                str(len(block_scores)),
                str(int(avg_duration)),
                str(int(avg_score * 100)),
            ])
            current_model = row[0]
            current_comments = row[6]
            block_scores = [float(row[3])]
            block_durations = [float(row[5])]

    avg_score = sum(block_scores) / len(block_scores)
    avg_duration = sum(block_durations) / len(block_durations)
    blocks.append([
        current_model,
        current_comments,
        str(len(block_scores)),
        str(int(avg_duration)),
        str(int(avg_score * 100)),
    ])

    if blocks:
        print()
        print('Average results per model and parameters:')
        print()
        block_headers = ["model", "comments", "rows", "seconds", "score"]
        block_align = ['l', 'l', 'r', 'r', 'r']
        draw_table(block_headers, blocks, block_align)


if __name__ == "__main__":
    main()
