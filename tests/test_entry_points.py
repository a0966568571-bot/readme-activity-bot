"""The main() of next_version.py and render_release_notes.py, as CI calls them."""
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import next_version as nv  # noqa: E402
import render_release_notes as rn  # noqa: E402


class NextVersionMainTests(unittest.TestCase):
    def test_reads_version_and_tags_and_writes_output(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "VERSION"), "w") as f:
                f.write("1.0\n")
            out = os.path.join(d, "out")
            tags = subprocess.CompletedProcess([], 0, stdout="dev-v1.0.3\nprod-v1.0.2\nv0.9\n")
            cwd = os.getcwd()
            os.chdir(d)
            try:
                with mock.patch.object(nv.subprocess, "run", return_value=tags), \
                        mock.patch.dict(os.environ, {"GITHUB_OUTPUT": out}), \
                        mock.patch("builtins.print"):
                    nv.main()
            finally:
                os.chdir(cwd)
            with open(out) as f:
                self.assertEqual(f.read(), "version=1.0.4\n")


class RenderNotesMainTests(unittest.TestCase):
    def test_writes_fallback_notes_when_agent_output_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            commits, out = os.path.join(d, "commits.txt"), os.path.join(d, "notes.md")
            with open(commits, "w") as f:
                f.write("abc1234 First change\n\n")
            with mock.patch.object(sys, "argv", ["x", "1.2.3", "prod-v1.2.2", commits, out]), \
                    mock.patch.dict(os.environ, {"AGENT_OUTPUT": ""}):
                rn.main()
            with open(out) as f:
                notes = f.read()
        self.assertIn("1.2.3", notes)
        self.assertIn("abc1234 First change", notes)


if __name__ == "__main__":
    unittest.main()
