"""report_metrics.py: loading runs through gh, the Markdown report and the CLI."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import report_metrics as r  # noqa: E402

RUNS = [
    {"databaseId": 3, "event": "schedule", "conclusion": "success", "createdAt": "2026-10-05T18:00:00Z",
     "startedAt": "2026-10-05T18:00:05Z", "updatedAt": "2026-10-05T18:01:00Z", "headBranch": "main"},
    {"databaseId": 2, "event": "push", "conclusion": "success", "createdAt": "2026-10-05T17:30:00Z",
     "startedAt": "2026-10-05T17:30:05Z", "updatedAt": "2026-10-05T17:31:00Z", "headBranch": "main"},
    {"databaseId": 1, "event": "push", "conclusion": "success", "createdAt": "2026-10-04T00:00:00Z",
     "startedAt": None, "updatedAt": None, "headBranch": "main"},       # before --since
    {"databaseId": 4, "event": "push", "conclusion": "", "createdAt": "2026-10-05T18:30:00Z",
     "startedAt": None, "updatedAt": None, "headBranch": "main"},       # still running
    {"databaseId": 5, "event": "pull_request", "conclusion": "success", "createdAt": "2026-10-05T18:40:00Z",
     "startedAt": None, "updatedAt": None, "headBranch": "feature"},    # not main
]


def fake_gh(*args):
    if args[:2] == ("run", "list"):
        return json.dumps(RUNS)
    run_id, target = args[2], args[args.index("-D") + 1]
    if run_id == "3":
        raise subprocess.CalledProcessError(1, "gh")                   # artifact expired
    os.makedirs(target)
    with open(os.path.join(target, "metrics.json"), "w") as f:
        json.dump({"api_calls": 3, "cache_hits": 1, "changed": True, "duration_seconds": 1.5,
                   "retries": 0, "wait_seconds": 0.0,
                   "endpoints": {"commits": 200}}, f)
    return ""


class LoadRunsTests(unittest.TestCase):
    def test_filters_downloads_and_sorts(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(r, "gh", side_effect=fake_gh):
            runs = r.load_runs("o/r", "2026-10-05T00:00:00Z", d)
        self.assertEqual([x["databaseId"] for x in runs], [2, 3])      # oldest first
        self.assertEqual(runs[0]["metrics"]["api_calls"], 3)
        self.assertIsNone(runs[1]["metrics"])                          # failed download is kept as None


class RenderTests(unittest.TestCase):
    def test_table_rows(self):
        runs = [dict(RUNS[1], metrics={"changed": True, "api_calls": 3, "cache_hits": 1,
                                       "duration_seconds": 1.5, "endpoints": {"commits": 200}}),
                dict(RUNS[0], metrics=None)]
        md = r.render_markdown({"runs": 2, "runs_by_event": {"push": 1, "schedule": 1}, "x": None},
                               runs, "2026-10-05T00:00:00Z")
        self.assertIn("| runs_by_event | push: 1, schedule: 1 |", md)
        self.assertIn("| x | - |", md)
        self.assertIn("| 2026-10-05T17:30:00Z | push | success | True | 3 | 1 | 1.5 | commits:200 |", md)
        self.assertIn("| 2026-10-05T18:00:00Z | schedule | success | - | - | - | - | - |", md)


class MainTests(unittest.TestCase):
    def test_writes_report_and_json(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(r, "gh", side_effect=fake_gh), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            rc = r.main(["--since", "2026-10-05T00:00:00Z", "--repo", "o/r",
                         "--out", os.path.join(d, "rep", "report.md"), "--json", os.path.join(d, "rep", "r.json")])
            with open(os.path.join(d, "rep", "report.md")) as f:
                self.assertIn("# Update README: run report", f.read())
            with open(os.path.join(d, "rep", "r.json")) as f:
                self.assertEqual(json.load(f)["summary"]["runs"], 2)
        self.assertEqual(rc, 0)

    def test_repo_is_required(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch("sys.stderr", new_callable=io.StringIO), \
                self.assertRaises(SystemExit) as ctx:
            r.main(["--since", "2026-10-05T00:00:00Z"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
