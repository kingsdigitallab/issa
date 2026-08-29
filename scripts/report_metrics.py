#!/usr/bin/env python3
"""Produce a paste-ready Markdown metrics table.

Combines: (a) commit activity, cloned fresh from GitHub for each run so
it's always current; (b) GitHub traffic data accumulated in
docs/metrics/traffic.json by scripts/collect_metrics.py; (c) manual
figures (record/reuse) passed in as arguments, since those aren't
scrapeable from any API.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

REPOS = ["issa", "framesense"]
CLONE_URLS = {name: f"https://github.com/kingsdigitallab/{name}.git" for name in REPOS}
STORE_PATH = Path(__file__).resolve().parent.parent / "docs" / "metrics" / "traffic.json"

MISSING = "collection begins this period"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="from_date", required=True, help="ISO start date, e.g. 2026-08-01")
    parser.add_argument("--to", dest="to_date", required=True, help="ISO end date, e.g. 2026-08-26")
    parser.add_argument("--record-period", default="—")
    parser.add_argument("--record-total", default="—")
    parser.add_argument("--reuse-period", default="—")
    parser.add_argument("--reuse-total", default="—")
    parser.add_argument("--reuse-note", default="—")
    return parser.parse_args()


def commit_counts(repo: str, since: str, until: str) -> tuple[int, int]:
    with tempfile.TemporaryDirectory() as tmp:
        clone_dir = Path(tmp) / repo
        subprocess.run(
            ["git", "clone", "--bare", "--filter=blob:none", "--quiet", CLONE_URLS[repo], str(clone_dir)],
            check=True,
        )
        period = subprocess.run(
            ["git", "-C", str(clone_dir), "rev-list", "--count",
             f"--since={since}", f"--until={until} 23:59:59", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        total = subprocess.run(
            ["git", "-C", str(clone_dir), "rev-list", "--count", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    return int(period), int(total)


def load_store() -> dict:
    if not STORE_PATH.exists():
        return {}
    return json.loads(STORE_PATH.read_text())


def in_window(day: str, since: str, until: str) -> bool:
    return since <= day <= until


def sum_daily(store: dict, section: str, since: str, until: str) -> tuple[int, int, int, int, int, int]:
    """Returns (period_count, period_uniques, period_days, total_count, total_uniques, total_days)."""
    period_count = period_uniques = total_count = total_uniques = 0
    period_days = total_days = 0
    for repo in REPOS:
        for day, entry in store.get(repo, {}).get(section, {}).items():
            total_count += entry["count"]
            total_uniques += entry["uniques"]
            total_days += 1
            if in_window(day, since, until):
                period_count += entry["count"]
                period_uniques += entry["uniques"]
                period_days += 1
    return (period_count, period_uniques, period_days, total_count, total_uniques, total_days)


def top_referrers(store: dict, since: str, until: str | None, limit: int = 3) -> str:
    totals: dict[str, int] = {}
    any_snapshot = False
    for repo in REPOS:
        for run_date, snapshot in store.get(repo, {}).get("referrers", {}).items():
            if until is not None and not in_window(run_date, since, until):
                continue
            any_snapshot = True
            for ref in snapshot:
                totals[ref["referrer"]] = totals.get(ref["referrer"], 0) + ref["count"]
    if not any_snapshot:
        return MISSING
    if not totals:
        return "none recorded"
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return ", ".join(f"{name} ({count})" for name, count in ranked)


def goatcounter_row(store: dict, since: str, until: str) -> tuple[str, str, str]:
    """GoatCounter's stored figure is an all-time cumulative visitor count,
    snapshotted daily (not a per-day delta like GitHub views). So the period
    figure is the difference between the latest snapshot at-or-before the
    window end and the latest snapshot strictly before the window start —
    not a sum of snapshots, which would double-count."""
    note = "GoatCounter dashboard: all-time cumulative total, snapshotted daily; period = delta between snapshots"
    not_configured = "GoatCounter not yet configured (GOATCOUNTER_API/GOATCOUNTER_TOKEN)"

    dated = sorted(
        (day, entry["visitors"])
        for day, entry in store.get("goatcounter", {}).items()
        if entry.get("visitors") is not None
    )
    if not dated:
        return "—", "—", not_configured

    def value_at_or_before(day: str) -> int | None:
        candidates = [v for d, v in dated if d <= day]
        return candidates[-1] if candidates else None

    def value_before(day: str) -> int | None:
        candidates = [v for d, v in dated if d < day]
        return candidates[-1] if candidates else None

    total_val = dated[-1][1]
    baseline = value_before(since)
    end_val = value_at_or_before(until)
    period_val = str(end_val - baseline) if baseline is not None and end_val is not None else MISSING

    return period_val, str(total_val), note


def format_views_row(store: dict, since: str, until: str) -> tuple[str, str, str, str]:
    period_count, period_uniques, period_days, total_count, total_uniques, total_days = sum_daily(
        store, "views", since, until
    )
    period_views = str(period_count) if period_days else MISSING
    total_views = str(total_count) if total_days else MISSING
    period_uv = str(period_uniques) if period_days else MISSING
    total_uv = str(total_uniques) if total_days else MISSING
    return period_uv, total_uv, period_views, total_views


def build_table(args: argparse.Namespace) -> str:
    since, until = args.from_date, args.to_date
    store = load_store()

    commits = {repo: commit_counts(repo, since, until) for repo in REPOS}
    activity_period = "/".join(str(commits[r][0]) for r in REPOS)
    activity_total = "/".join(str(commits[r][1]) for r in REPOS)

    period_uv, total_uv, period_views, total_views = format_views_row(store, since, until)
    gc_period, gc_total, gc_note = goatcounter_row(store, since, until)
    ref_period = top_referrers(store, since, until)
    ref_total = top_referrers(store, since, None)

    header = f"| Dimension | Metric | This period ({since}–{until}) | Total | Notes / source |"
    sep = "|---|---|---|---|---|"
    rows = [
        f"| Record | Manual entry | {args.record_period} | {args.record_total} | Manual entry — not derived from telemetry |",
        f"| Reach | Unique visitors | {period_uv} | {total_uv} | Summed per-day uniques, not deduplicated across the window |",
        f"| Reach | Page views | {period_views} | {total_views} | Sums exactly across days |",
        f"| Reach | Dashboard visitors | {gc_period} | {gc_total} | {gc_note} |",
        f"| Reach | Notable referrers | {ref_period} | {ref_total} | GitHub traffic referrer snapshots (top 3) |",
        f"| Reuse | Manual entry | {args.reuse_period} | {args.reuse_total} | {args.reuse_note} |",
        f"| Activity | Commits (ISSA/FrameSense) | {activity_period} | {activity_total} | git log, default branch |",
    ]
    return "\n".join([header, sep, *rows])


def main() -> None:
    args = parse_args()
    print(build_table(args))


if __name__ == "__main__":
    main()
