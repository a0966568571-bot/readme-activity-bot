import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import report_metrics as r  # noqa: E402


def run(created, event="schedule", changed=False, calls=3, hits=3, conclusion="success"):
    return {"createdAt": created, "startedAt": created, "updatedAt": created, "event": event,
            "conclusion": conclusion,
            "metrics": {"api_calls": calls, "cache_hits": hits, "changed": changed, "retries": 0,
                        "wait_seconds": 0.0, "duration_seconds": 1.0}}


class ReportTests(unittest.TestCase):
    def test_schedule_delay(self):
        self.assertEqual(r.schedule_delay_minutes(datetime(2026, 10, 5, 17, 41, 30)), 4.5)
        self.assertEqual(r.schedule_delay_minutes(datetime(2026, 10, 5, 18, 7, 0)), 0)

    def test_summary(self):
        runs = [run("2026-10-05T17:24:15Z", event="push", changed=True, hits=0),
                run("2026-10-05T17:40:00Z"),
                run("2026-10-05T17:55:00Z"),
                {"createdAt": "2026-10-05T18:10:00Z", "startedAt": None, "updatedAt": None,
                 "event": "schedule", "conclusion": "failure", "metrics": None}]
        s = r.summarize(runs)
        self.assertEqual(s["runs"], 4)
        self.assertEqual(s["runs_by_event"], {"push": 1, "schedule": 3})
        self.assertEqual(s["success_rate_pct"], 75.0)
        self.assertEqual(s["commits_made"], 1)
        self.assertEqual(s["commits_avoided"], 2)
        self.assertEqual(s["cache_hit_rate_pct"], round(100 * 6 / 9, 1))
        self.assertEqual(s["max_schedule_delay_min"], 3.0)

    def test_empty(self):
        s = r.summarize([])
        self.assertEqual(s["runs"], 0)
        self.assertIsNone(s["cache_hit_rate_pct"])


if __name__ == "__main__":
    unittest.main()
