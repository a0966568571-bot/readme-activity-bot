import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ci"))
import junit_summary as j  # noqa: E402

PASSING = """<?xml version="1.0"?><testsuites><testsuite name="pytest" errors="0" failures="0"
 skipped="1" tests="3" time="0.50"><testcase classname="a.T" name="test_1"/>
 <testcase classname="a.T" name="test_2"/><testcase classname="a.T" name="test_3"><skipped/></testcase>
</testsuite></testsuites>"""

FAILING = """<?xml version="1.0"?><testsuites><testsuite name="pytest" errors="1" failures="1"
 skipped="0" tests="4" time="1.25"><testcase classname="b.T" name="test_ok"/>
 <testcase classname="b.T" name="test_x"><failure message="AssertionError: 1 | 2 != 3&#10;more">tb</failure></testcase>
 <testcase classname="b.T" name="test_y"><error message="">boom</error></testcase>
 <testcase classname="b.T" name="test_z"/></testsuite></testsuites>"""


class JunitSummaryTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def write(self, folder, name, text):
        os.makedirs(os.path.join(self.dir.name, folder), exist_ok=True)
        with open(os.path.join(self.dir.name, folder, name), "w") as f:
            f.write(text)

    def test_counts_and_failures(self):
        self.write("unit-results-py3.9", "unit.xml", PASSING)
        self.write("integration-prod-results-py3.13", "integration.xml", FAILING)
        self.write("unit-results-py3.9", "coverage.xml", "<coverage/>")   # not a test report
        runs = j.collect(self.dir.name)
        self.assertEqual([r[0] for r in runs], ["integration-prod-results-py3.13", "unit-results-py3.9"])
        self.assertEqual(j.totals(runs), {"tests": 7, "passed": 4, "failed": 2, "skipped": 1, "runs": 2})
        md = j.render(runs)
        self.assertIn("❌ Test report: 4 passed, 2 failed, 1 skipped (2 runs)", md)
        self.assertIn("| ❌ integration-prod-results-py3.13 | 4 | 2 | 2 | 0 | 1.25 |", md)
        self.assertIn("b.T.test_x: AssertionError: 1 \\| 2 != 3", md)   # first line only, pipe escaped
        self.assertIn("b.T.test_y: boom", md)
        self.assertNotIn("more", md)

    def test_badges(self):
        self.assertEqual(j.badge({"runs": 2, "failed": 0, "passed": 9})["message"], "9 passed")
        self.assertEqual(j.badge({"runs": 2, "failed": 2, "passed": 9})["color"], "red")
        self.assertEqual(j.badge({"runs": 0, "failed": 0, "passed": 0})["message"], "no results")

    def test_main_writes_json_and_badge(self):
        self.write("unit", "unit.xml", PASSING)
        out_json = os.path.join(self.dir.name, "t.json")
        badges = os.path.join(self.dir.name, "badges")
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            j.main([self.dir.name, "--json", out_json, "--badge-dir", badges])
        self.assertIn("✅ Test report: 2 passed", out.getvalue())
        with open(out_json) as f:
            self.assertEqual(json.load(f)["skipped"], 1)
        with open(os.path.join(badges, "tests.json")) as f:
            self.assertEqual(json.load(f)["color"], "brightgreen")

    def test_no_results_is_reported(self):
        self.assertIn("No JUnit files were found", j.render(j.collect(self.dir.name)))


if __name__ == "__main__":
    unittest.main()
