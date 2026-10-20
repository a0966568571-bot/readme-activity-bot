#!/usr/bin/env python3
"""Turn the JUnit XML files from every test job into one Markdown report.

Usage: junit_summary.py RESULTS_DIR [--json totals.json] [--badge-dir DIR]

RESULTS_DIR holds one folder per downloaded artifact (unit-results-ubuntu-latest-py3.9/,
integration-staging-results-py3.13/, ...), each with *.xml from pytest --junitxml.
The Markdown goes to stdout: a table per test run, then every failure with its message.
--json writes the totals; --badge-dir writes a shields.io endpoint file, tests.json.
Standard library only, and runs on Python 3.9.
"""
import argparse
import glob
import json
import os
import sys
import xml.etree.ElementTree as ET


def read_suite(path):
    """Counts and failures of one JUnit file. pytest writes <testsuites><testsuite ...>."""
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    counts = {"tests": 0, "failed": 0, "skipped": 0, "time": 0.0}
    failures = []
    for s in suites:
        counts["tests"] += int(s.get("tests", 0))
        counts["failed"] += int(s.get("failures", 0)) + int(s.get("errors", 0))
        counts["skipped"] += int(s.get("skipped", 0))
        counts["time"] += float(s.get("time", 0))
        for case in s.iter("testcase"):
            for tag in ("failure", "error"):
                bad = case.find(tag)
                if bad is not None:
                    message = (bad.get("message") or bad.text or "").strip().splitlines()
                    failures.append("%s.%s: %s" % (case.get("classname"), case.get("name"),
                                                   (message[0] if message else tag)[:200]))
    counts["passed"] = counts["tests"] - counts["failed"] - counts["skipped"]
    return counts, failures


def collect(results_dir):
    """[(run name, counts, failures)] sorted by name. The run name is the artifact folder."""
    runs = []
    for path in sorted(glob.glob(os.path.join(results_dir, "**", "*.xml"), recursive=True)):
        if os.path.basename(path) == "coverage.xml":
            continue
        counts, failures = read_suite(path)
        name = os.path.relpath(os.path.dirname(path), results_dir).split(os.sep)[0]
        runs.append((name if name != "." else os.path.basename(path), counts, failures))
    return runs


def totals(runs):
    t = {"tests": 0, "passed": 0, "failed": 0, "skipped": 0}
    for _, c, _ in runs:
        for k in t:
            t[k] += c[k]
    t["runs"] = len(runs)
    return t


def render(runs):
    t = totals(runs)
    icon = "❌" if t["failed"] else "✅"
    lines = ["### %s Test report: %d passed, %d failed, %d skipped (%d runs)"
             % (icon, t["passed"], t["failed"], t["skipped"], t["runs"]), "",
             "| Test run | Tests | Passed | Failed | Skipped | Time (s) |", "|---|---|---|---|---|---|"]
    for name, c, _ in runs:
        lines.append("| %s%s | %d | %d | %d | %d | %.2f |" % ("❌ " if c["failed"] else "", name, c["tests"],
                                                           c["passed"], c["failed"], c["skipped"], c["time"]))
    failures = [(name, f) for name, _, fs in runs for f in fs]
    if failures:
        lines += ["", "#### Failures", ""]
        lines += ["- `%s` %s" % (name, f.replace("|", "\\|")) for name, f in failures]
    if not runs:
        lines += ["", "No JUnit files were found. Did the test jobs run?"]
    return "\n".join(lines) + "\n"


def badge(t):
    if not t["runs"]:
        return {"schemaVersion": 1, "label": "tests", "message": "no results", "color": "lightgrey"}
    if t["failed"]:
        return {"schemaVersion": 1, "label": "tests", "message": "%d failed" % t["failed"], "color": "red"}
    return {"schemaVersion": 1, "label": "tests", "message": "%d passed" % t["passed"], "color": "brightgreen"}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("results_dir")
    p.add_argument("--json", help="write the totals here")
    p.add_argument("--badge-dir", help="write tests.json (shields.io endpoint) here")
    args = p.parse_args(argv)

    runs = collect(args.results_dir)
    sys.stdout.write(render(runs))
    t = totals(runs)
    if args.json:
        with open(args.json, "w") as f:
            json.dump(t, f)
    if args.badge_dir:
        os.makedirs(args.badge_dir, exist_ok=True)
        with open(os.path.join(args.badge_dir, "tests.json"), "w") as f:
            json.dump(badge(t), f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
