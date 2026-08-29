#!/usr/bin/env python3
"""Snapshot GitHub traffic data into docs/metrics/traffic.json.

GitHub's Traffic API (views/clones/referrers) only retains a rolling
14-day window, so this must run at least that often to avoid gaps.
Safe to run repeatedly: same-date entries are overwritten, never
duplicated.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPOS = ["kingsdigitallab/issa", "kingsdigitallab/framesense"]
API_ROOT = "https://api.github.com"
STORE_PATH = Path(__file__).resolve().parent.parent / "docs" / "metrics" / "traffic.json"

# GoatCounter's /stats/total defaults to a rolling last-7-days window if no
# start/end is given. We want an all-time cumulative total instead, so we
# anchor "start" at a fixed date safely before any realistic site creation
# (GoatCounter itself launched in 2018) rather than the true site start date,
# which we don't know and don't need to.
GOATCOUNTER_EPOCH = "2018-01-01T00:00:00Z"


def github_get(path: str, token: str) -> dict:
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors="replace")
        raise RuntimeError(f"GitHub API {path} failed: {error.code} {body}") from error


def merge_daily(section: dict, entries: list[dict]) -> None:
    for entry in entries:
        date = entry["timestamp"][:10]
        section[date] = {"count": entry["count"], "uniques": entry["uniques"]}


def collect_repo(full_name: str, token: str, store: dict, run_date: str) -> None:
    short_name = full_name.split("/")[-1]
    repo_store = store.setdefault(short_name, {"views": {}, "clones": {}, "referrers": {}})

    views = github_get(f"/repos/{full_name}/traffic/views?per=day", token)
    merge_daily(repo_store["views"], views.get("views", []))

    clones = github_get(f"/repos/{full_name}/traffic/clones?per=day", token)
    merge_daily(repo_store["clones"], clones.get("clones", []))

    referrers = github_get(f"/repos/{full_name}/traffic/popular/referrers", token)
    repo_store["referrers"][run_date] = [
        {"referrer": r["referrer"], "count": r["count"], "uniques": r["uniques"]}
        for r in referrers
    ]


def collect_goatcounter(store: dict, run_date: str) -> None:
    api_base = os.environ.get("GOATCOUNTER_API")
    if not api_base:
        return

    token = os.environ.get("GOATCOUNTER_TOKEN")
    if not token:
        print(
            "GOATCOUNTER_API is set but GOATCOUNTER_TOKEN is not; "
            "skipping GoatCounter collection.",
            file=sys.stderr,
        )
        return

    end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00:00Z")
    query = urllib.parse.urlencode({"start": GOATCOUNTER_EPOCH, "end": end})
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}/api/v0/stats/total?{query}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors="replace")
        print(f"GoatCounter API failed: {error.code} {body}", file=sys.stderr)
        return

    # "total" is the all-time (since GOATCOUNTER_EPOCH) visitor count as of
    # this run — a monotonically increasing cumulative counter, not a daily
    # delta. The reporter derives period figures by diffing two snapshots.
    store.setdefault("goatcounter", {})[run_date] = {"visitors": data.get("total")}


def main() -> None:
    token = os.environ.get("METRICS_PAT")
    if not token:
        raise SystemExit("METRICS_PAT environment variable is required")

    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    store = json.loads(STORE_PATH.read_text()) if STORE_PATH.exists() else {}

    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for full_name in REPOS:
        collect_repo(full_name, token, store, run_date)

    collect_goatcounter(store, run_date)

    STORE_PATH.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {STORE_PATH}")


if __name__ == "__main__":
    main()
