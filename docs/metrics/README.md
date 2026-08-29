# Metrics

Automated collection and on-demand reporting of GitHub traffic and
activity data for `kingsdigitallab/issa` and `kingsdigitallab/framesense`,
used for BFI reporting.

## What runs, and when

`.github/workflows/metrics.yml` runs `scripts/collect_metrics.py` daily
at 06:00 UTC (and on manual `workflow_dispatch`). It calls the GitHub
Traffic API (`/traffic/views`, `/traffic/clones`,
`/traffic/popular/referrers`) for both repos, merges the results into
[`traffic.json`](traffic.json), and commits the file if it changed. The
commit message ends `[skip ci]` so it doesn't retrigger other workflows,
and the job doesn't fail when there's nothing new to commit.

### Why daily

GitHub's Traffic API only retains a rolling **14-day window** — data
older than that is silently dropped from the API response, not archived
anywhere. Running daily leaves a wide safety margin against a missed run
(a workflow outage, a paused schedule) still causing permanent data
loss. `traffic.json` is the durable, append-only record; the API itself
is not.

## Authentication

The collector calls the API with `Authorization: token $METRICS_PAT`,
where `METRICS_PAT` is a **classic PAT with `repo` scope**, stored as an
Actions secret on this repository. The Traffic API requires push access
to the repo it's reading, which only a classic PAT (or an org-level
fine-grained token) can grant here — **org-level fine-grained PATs
weren't available/set up for this org at the time this was built**, so a
classic PAT was used instead as the pragmatic option. If fine-grained
org tokens become available, `METRICS_PAT` can be swapped for one scoped
to just `administration:read` + `contents:write` on the two target
repos, with no code changes needed.

The same secret is reused by the workflow to check out and push commits
(via `actions/checkout`'s `token:` input), so the bot commit is
attributed to whichever account owns the PAT.

## GoatCounter (optional)

If `GOATCOUNTER_API` and `GOATCOUNTER_TOKEN` are both set as Actions
secrets, the collector also snapshots an all-time cumulative visitor
count from your GoatCounter site into `traffic.json`, keyed by run date.
If either is unset, this step is skipped cleanly and the reporter prints
`—` for "Dashboard visitors" with a note that it isn't configured.

**To enable it, you need two things from GoatCounter:**

1. **`GOATCOUNTER_API`** — your site's base URL, e.g.
   `https://issa.goatcounter.com` (the subdomain you chose when creating
   the site — find it in the GoatCounter admin, top of the page).
2. **`GOATCOUNTER_TOKEN`** — an API key. Create one from
   **[your username in the top menu] → API → New**. A read-only key is
   enough — this integration only calls `GET /api/v0/stats/total`, it
   never writes anything.

Add both as **repository secrets** (Settings → Secrets and variables →
Actions → New repository secret) with those exact names.

### How the number is derived

GoatCounter's `/api/v0/stats/total` endpoint returns a visitor count for
an arbitrary date range — by default just the last 7 days, which isn't
useful for an all-time figure. The collector explicitly requests the
range from a fixed anchor date (2018-01-01, safely before any realistic
site creation date) through "now", so each day's snapshot is an
**all-time cumulative total as of that run** — not a daily delta.

The reporter (`goatcounter_row` in `report_metrics.py`) accounts for
that: the "Total" column is just the latest snapshot, and the "This
period" column is the *difference* between the snapshot nearest the end
of the window and the snapshot immediately before its start — i.e. the
net increase over the period, not a sum of snapshots (summing cumulative
totals would wildly overcount).

## Running the reporter

`scripts/report_metrics.py` produces a paste-ready Markdown table for a
given date range. It doesn't run automatically — run it manually
whenever a report is due:

```bash
python scripts/report_metrics.py \
  --from 2026-08-01 --to 2026-08-26 \
  --record-period "..." --record-total "..." \
  --reuse-period "..." --reuse-total "..." \
  --reuse-note "..."
```

- `--from`/`--to`: ISO dates bounding "this period".
- `--record-*` / `--reuse-*`: manual figures (e.g. press mentions,
  dataset citations) that aren't available from any API — supply
  current values by hand each time you run a report.

The reporter clones both repos fresh (bare, blobless) each run to count
commits, and reads `traffic.json` for view/unique/referrer/GoatCounter
figures — it doesn't call any API itself, so no token is needed to run
it. If `traffic.json` has no data covering the requested window, the
affected cells print `collection begins this period` instead of a
number, rather than silently showing a misleading zero.

Note: summed page views are exact (GitHub's daily counts sum cleanly),
but summed unique visitors are **unique-per-day, summed** — not
deduplicated across the window — so that figure is an upper bound on
true distinct visitors over the period, not an exact count.
