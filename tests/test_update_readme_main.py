"""Unit tests for the parts of update_readme.py the first tests did not reach:
the HTTP layer, the ETag cache, collect(), the CLI modes and the run summary."""
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import update_readme as u  # noqa: E402

README = "# Title\n\n%s\nold\n%s\n\nfooter\n" % (u.START, u.END)


def commit(sha, message, login="alice", date="2026-10-05T10:00:00Z"):
    return {"sha": sha, "html_url": "https://x/" + sha, "author": {"login": login},
            "commit": {"message": message, "author": {"name": login, "date": date}}}


class FakeResponse(io.BytesIO):
    status = 200
    headers = {"ETag": '"v1"', "X-RateLimit-Remaining": "42"}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class SendTests(unittest.TestCase):
    def setUp(self):
        self.cfg = u.Config({})
        self.metrics = u.new_metrics()

    def test_ok_lowercases_headers(self):
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(b"[]")):
            status, headers, body = u._send("https://api/x", {}, self.cfg, self.metrics)
        self.assertEqual((status, body), (200, b"[]"))
        self.assertEqual(headers["etag"], '"v1"')
        self.assertEqual(self.metrics["api_calls"], 1)

    def test_http_error_returns_status(self):
        err = urllib.error.HTTPError("https://api/x", 404, "Not Found", {"X-A": "1"}, io.BytesIO(b"nf"))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            status, headers, body = u._send("https://api/x", {}, self.cfg, self.metrics)
        self.assertEqual((status, headers, body), (404, {"x-a": "1"}, b"nf"))

    def test_network_error_is_status_0(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            self.assertEqual(u._send("https://api/x", {}, self.cfg, self.metrics), (0, {}, b""))


class FetchJsonTests(unittest.TestCase):
    def setUp(self):
        self.cfg = u.Config({"MAX_RETRIES": "2", "MAX_WAIT": "0"})
        self.metrics = u.new_metrics()
        self.cache = {}

    def fetch(self, replies):
        with mock.patch.object(u, "_send", side_effect=replies) as send:
            data = u.fetch_json("/repos/o/r/commits?per_page=30", "tok", self.cache, self.cfg,
                                self.metrics, sleep=lambda s: None)
        return data, send

    def test_200_fills_cache_then_304_uses_it(self):
        data, _ = self.fetch([(200, {"etag": '"e1"', "x-ratelimit-remaining": "9"}, b'[1, 2]')])
        self.assertEqual(data, [1, 2])
        self.assertEqual(self.metrics["rate_limit_remaining"], 9)
        self.assertEqual(self.metrics["endpoints"], {"commits": 200})

        data, send = self.fetch([(304, {}, b"")])
        self.assertEqual(data, [1, 2])
        self.assertEqual(self.metrics["cache_hits"], 1)
        self.assertEqual(send.call_args[0][1]["If-None-Match"], '"e1"')

    def test_network_error_is_retried(self):
        data, send = self.fetch([(0, {}, b""), (200, {}, b"{}")])
        self.assertEqual(data, {})
        self.assertEqual(send.call_count, 2)
        self.assertEqual(self.metrics["retries"], 1)

    def test_404_fails_at_once(self):
        with self.assertRaises(SystemExit) as ctx:
            self.fetch([(404, {}, b"")])
        self.assertIn("HTTP 404", str(ctx.exception))


class CacheTests(unittest.TestCase):
    def test_round_trip_and_bad_file(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = u.Config({"CACHE_DIR": os.path.join(d, "c")})
            self.assertEqual(u.load_cache(cfg), {})            # no file yet
            u.save_cache(cfg, {"k": {"etag": "e", "data": 1}})
            self.assertEqual(u.load_cache(cfg), {"k": {"etag": "e", "data": 1}})
            with open(os.path.join(d, "c", "etag-cache.json"), "w") as f:
                f.write("not json")
            self.assertEqual(u.load_cache(cfg), {})            # corrupt cache is ignored


class CollectTests(unittest.TestCase):
    def test_filters_and_sorts(self):
        commits = [commit("a1", "chore(readme): bot", "github-actions[bot]"), commit("b2", "Real work")]
        pulls = [{"number": 1, "merged_at": None},
                 {"number": 2, "merged_at": "2026-10-01T00:00:00Z"},
                 {"number": 3, "merged_at": "2026-10-03T00:00:00Z"}]
        issues = [{"number": 4, "closed_at": "2026-10-02T00:00:00Z"},
                  {"number": 5, "closed_at": "2026-10-04T00:00:00Z", "pull_request": {}}]
        cfg = u.Config({"ITEM_LIMIT": "1"})
        with mock.patch.object(u, "fetch_json", side_effect=[commits, pulls, issues]):
            c, p, i = u.collect("o/r", "tok", {}, cfg, u.new_metrics())
        self.assertEqual([x["sha"] for x in c], ["b2"])
        self.assertEqual([x["number"] for x in p], [3])        # newest merged PR only
        self.assertEqual([x["number"] for x in i], [4])        # PRs are not issues


class MainTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.readme = os.path.join(self.dir.name, "README.md")
        with open(self.readme, "w") as f:
            f.write(README)
        self.env = {"GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": "o/r",
                    "CACHE_DIR": os.path.join(self.dir.name, ".cache"),
                    "METRICS_PATH": os.path.join(self.dir.name, "metrics.json"),
                    "GITHUB_OUTPUT": os.path.join(self.dir.name, "out"),
                    "GITHUB_STEP_SUMMARY": os.path.join(self.dir.name, "summary.md")}
        self.data = ([commit("abc1234", "Hello")], [], [])

    def main(self, *args, env=None):
        with mock.patch.dict(os.environ, env if env is not None else self.env, clear=True), \
                mock.patch.object(u, "collect", return_value=self.data), \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            rc = u.main(list(args) + ["--readme", self.readme])
        return rc, out.getvalue()

    def read(self, name):
        with open(os.path.join(self.dir.name, name)) as f:
            return f.read()

    def test_check_mode(self):
        self.assertEqual(self.main("--check", env={}), (0, "Markers OK in %s\n" % self.readme))

    def test_bad_markers(self):
        with open(self.readme, "w") as f:
            f.write("no markers")
        rc, out = self.main("--check", env={})
        self.assertEqual(rc, 1)
        self.assertIn("::error file=", out)

    def test_needs_token_and_repo(self):
        rc, out = self.main(env={})
        self.assertEqual(rc, 2)
        self.assertIn("must be set", out)

    def test_write_then_no_change(self):
        rc, out = self.main("--diff-out", os.path.join(self.dir.name, "d.diff"))
        self.assertEqual(rc, 0)
        self.assertIn("README.md updated.", out)
        self.assertIn("Hello", self.read("README.md"))
        self.assertIn("+- 2026-10-05", self.read("d.diff"))
        self.assertIn("changed=true", self.read("out"))
        self.assertIn("<summary>README diff</summary>", self.read("summary.md"))
        self.assertTrue(json.loads(self.read("metrics.json"))["changed"])

        rc, out = self.main()
        self.assertIn("No changes, README.md left as is.", out)
        self.assertIn("changed=false", self.read("out"))

    def test_dry_run_prints_diff_only(self):
        rc, out = self.main("--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("+- 2026-10-05", out)
        self.assertEqual(self.read("README.md"), README)
        self.assertEqual(json.loads(self.read("metrics.json"))["mode"], "dry-run")


if __name__ == "__main__":
    unittest.main()
