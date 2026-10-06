#!/usr/bin/env python3
"""Summarize the metrics.json artifacts of past "Update README" runs.

Needs the GitHub CLI (`gh`, preinstalled on GitHub-hosted runners) with GH_TOKEN
or a logged-in session that can read Actions.

  python3 scripts/report_metrics.py --since 2026-10-05T17:24:00Z \
      --out reports/metrics.md --json reports/metrics.json
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

WORKFLOW = "update-readme.yml"
SCHEDULE_MINUTES = (7, 22, 37, 52)   # the temporary 15-minute cron used while collecting data


def gh(*args):
    return subprocess.run(["gh"] + list(args), check=True, capture_output=True, text=True).stdout


def parse_time(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def schedule_delay_minutes(created):
    """Minutes between the cron slot and the moment GitHub created the run."""
    t = created.replace(second=0)
    for back in range(0, 60):
        slot = t - timedelta(minutes=back)
        if slot.minute in SCHEDULE_MINUTES:
            return round((created - slot).total_seconds() / 60, 1)
    return None


def load_runs(repo, since, workdir):
    fields = "databaseId,event,conclusion,createdAt,startedAt,updatedAt,headBranch"
    runs = json.loads(gh("run", "list", "-R", repo, "--workflow", WORKFLOW, "-L", "500", "--json", fields))
    out = []
    for r in runs:
        if r["headBranch"] != "main" or r["createdAt"] < since or not r["conclusion"]:
            continue
        run_id = str(r["databaseId"])
        target = os.path.join(workdir, run_id)
        try:
            gh("run", "download", run_id, "-R", repo, "-n", "metrics-" + run_id, "-D", target)
            with open(os.path.join(target, "metrics.json")) as f:
                r["metrics"] = json.load(f)
        except (subprocess.CalledProcessError, OSError, ValueError):
            r["metrics"] = None
        out.append(r)
    return sorted(out, key=lambda r: r["createdAt"])


def _pct(part, whole):
    return round(100.0 * part / whole, 1) if whole else None


def _avg(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 2) if values else None


def summarize(runs):
    m = [r["metrics"] for r in runs if r.get("metrics")]
    by_event = {}
    for r in runs:
        by_event[r["event"]] = by_event.get(r["event"], 0) + 1
    requests = sum(x["api_calls"] for x in m)
    hits = sum(x["cache_hits"] for x in m)
    changed = sum(1 for x in m if x["changed"])
    delays = [schedule_delay_minutes(parse_time(r["createdAt"])) for r in runs if r["event"] == "schedule"]
    walls = [(parse_time(r["updatedAt"]) - parse_time(r["startedAt"])).total_seconds()
             for r in runs if r.get("startedAt")]
    return {
        "runs": len(runs),
        "runs_by_event": by_event,
        "success_rate_pct": _pct(sum(1 for r in runs if r["conclusion"] == "success"), len(runs)),
        "runs_with_metrics": len(m),
        "commits_made": changed,
        "commits_avoided": len(m) - changed,
        "skip_rate_pct": _pct(len(m) - changed, len(m)),
        "api_requests": requests,
        "cache_hits_304": hits,
        "cache_hit_rate_pct": _pct(hits, requests),
        "rate_limit_points_saved": hits,   # a 304 does not count against the rate limit
        "retries": sum(x["retries"] for x in m),
        "retry_wait_seconds": round(sum(x["wait_seconds"] for x in m), 1),
        "avg_script_seconds": _avg([x["duration_seconds"] for x in m]),
        "avg_run_seconds": _avg(walls),
        "avg_schedule_delay_min": _avg(delays),
        "max_schedule_delay_min": max([d for d in delays if d is not None], default=None),
    }


def render_markdown(summary, runs, since):
    lines = ["# Update README: run report", "", "Runs on `main` since %s." % since, "",
             "| Metric | Value |", "|---|---|"]
    for k, v in summary.items():
        if isinstance(v, dict):
            v = ", ".join("%s: %s" % item for item in sorted(v.items()))
        lines.append("| %s | %s |" % (k, "-" if v is None else v))
    lines += ["", "## Runs", "", "| Created (UTC) | Event | Result | Changed | API calls | 304 hits | Script s | Endpoints |",
              "|---|---|---|---|---|---|---|---|"]
    for r in runs:
        x = r.get("metrics") or {}
        endpoints = " ".join("%s:%s" % e for e in sorted((x.get("endpoints") or {}).items())) or "-"
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["createdAt"], r["event"], r["conclusion"], x.get("changed", "-"),
            x.get("api_calls", "-"), x.get("cache_hits", "-"), x.get("duration_seconds", "-"), endpoints))
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarize Update README run metrics")
    parser.add_argument("--since", required=True, help="ISO time, e.g. 2026-10-05T17:24:00Z")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--out", help="write the Markdown report here")
    parser.add_argument("--json", help="write summary and runs as JSON here")
    args = parser.parse_args(argv)
    if not args.repo:
        parser.error("--repo or GITHUB_REPOSITORY is required")

    with tempfile.TemporaryDirectory() as workdir:
        runs = load_runs(args.repo, args.since, workdir)
    summary = summarize(runs)
    report = render_markdown(summary, runs, args.since)
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as f:
            f.write(report)
    if args.json:
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        with open(args.json, "w") as f:
            json.dump({"summary": summary, "runs": runs}, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
