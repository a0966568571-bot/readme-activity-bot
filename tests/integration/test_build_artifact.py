"""Integration tests: run the code inside build.zip, the same file that gets released.

Unit tests import scripts/ from the checkout. These tests do not: they unzip the
build artifact and run its update_readme.py as a separate process, against a fake
GitHub API on 127.0.0.1. No network and no real token are needed.

Settings (environment variables):
  BUILD_ZIP     path to the artifact                     (default build.zip)
  TEST_ENV      staging or prod                          (default staging)
  STAGING_ZIP   prod only: the zip published to staging; it must match BUILD_ZIP
  GITHUB_SHA    if set, BUILD_INFO must name this commit
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TEST_ENV = os.environ.get("TEST_ENV", "staging")
BUILD_ZIP = os.environ.get("BUILD_ZIP", "build.zip")

# Exactly what may ship. Anything else (tests, .github, caches, __pycache__) is a build bug.
REQUIRED = {"README.md", "LICENSE", "VERSION", "BUILD_INFO", "scripts/update_readme.py"}
ALLOWED = re.compile(r"^(README\.md|LICENSE|VERSION|BUILD_INFO|scripts/|scripts/[a-z_]+\.py)$")

REPO = "octo/demo"


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def commit(sha, message, login="alice"):
    return {"sha": sha, "html_url": "https://github.com/%s/commit/%s" % (REPO, sha),
            "author": {"login": login},
            "commit": {"message": message, "author": {"name": login, "date": "2026-10-20T08:00:00Z"}}}


FIXTURES = {
    "/repos/%s/commits" % REPO: [
        commit("a" * 40, "Add integration tests\n\nbody text"),
        commit("b" * 40, "chore(readme): update recent activity [skip ci]", "github-actions[bot]"),
        commit("c" * 40, "Fix <script> [x] escaping"),
    ],
    "/repos/%s/pulls" % REPO: [
        {"number": 21, "title": "Test gates", "html_url": "https://github.com/%s/pull/21" % REPO,
         "merged_at": "2026-10-20T09:00:00Z", "user": {"login": "bob"}},
        {"number": 20, "title": "Closed without merge", "html_url": "https://x/20",
         "merged_at": None, "user": {"login": "bob"}},
    ],
    "/repos/%s/issues" % REPO: [
        {"number": 19, "title": "Flaky build", "html_url": "https://github.com/%s/issues/19" % REPO,
         "closed_at": "2026-10-19T09:00:00Z"},
        {"number": 21, "title": "Test gates", "html_url": "https://x/21",
         "closed_at": "2026-10-20T09:00:00Z", "pull_request": {}},
    ],
}


class FakeGitHub(BaseHTTPRequestHandler):
    """Serves FIXTURES with ETags. `fail_next` makes the next N requests return 429."""
    fail_next = 0
    seen = []   # (path, If-None-Match, Authorization) of every request

    def do_GET(self):
        path = self.path.split("?")[0]
        FakeGitHub.seen.append((path, self.headers.get("If-None-Match"), self.headers.get("Authorization")))
        if FakeGitHub.fail_next > 0:
            FakeGitHub.fail_next -= 1
            self._reply(429, b'{"message": "slow down"}', {"Retry-After": "0"})
            return
        if path not in FIXTURES:
            self._reply(404, b'{"message": "Not Found"}')
            return
        body = json.dumps(FIXTURES[path]).encode()
        etag = '"%s"' % hashlib.sha1(body).hexdigest()
        if self.headers.get("If-None-Match") == etag:
            self._reply(304, b"", {"ETag": etag})
        else:
            self._reply(200, body, {"ETag": etag, "X-RateLimit-Remaining": "4999"})

    def _reply(self, status, body, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):   # keep the test log readable
        pass


class ArtifactTestCase(unittest.TestCase):
    """Unzips BUILD_ZIP once per class into a temp folder."""

    @classmethod
    def setUpClass(cls):
        if TEST_ENV not in ("staging", "prod"):
            raise RuntimeError("TEST_ENV must be staging or prod, got %r" % TEST_ENV)
        # A missing artifact is a failure, not a skip: a skipped gate would let the release through.
        if not os.path.isfile(BUILD_ZIP):
            raise RuntimeError("build artifact not found: %s (set BUILD_ZIP)" % BUILD_ZIP)
        cls.tmp = tempfile.mkdtemp(prefix="artifact-")
        with zipfile.ZipFile(BUILD_ZIP) as z:
            cls.names = z.namelist()
            z.extractall(cls.tmp)
        cls.app = os.path.join(cls.tmp, "scripts", "update_readme.py")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_app(self, *args, env=None, cwd=None):
        # Start from a clean environment so the real CI token and output files never leak in.
        base = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}
        base.update(env or {})
        return subprocess.run([sys.executable, self.app] + list(args), env=base, cwd=cwd or self.tmp,
                              capture_output=True, text=True, timeout=60)


class ArtifactContentsTests(ArtifactTestCase):
    def test_has_required_files(self):
        self.assertEqual(REQUIRED - set(self.names), set())

    def test_ships_nothing_else(self):
        extra = [n for n in self.names if not ALLOWED.match(n)]
        self.assertEqual(extra, [], "unexpected files in the artifact")

    def test_build_info(self):
        with open(os.path.join(self.tmp, "BUILD_INFO")) as f:
            info = dict(line.strip().split("=", 1) for line in f if "=" in line)
        with open(os.path.join(self.tmp, "VERSION")) as f:
            major_minor = f.read().strip()
        self.assertRegex(info.get("version", ""), r"^\d+\.\d+\.\d+$")
        self.assertTrue(info["version"].startswith(major_minor + "."),
                        "version %s does not match VERSION %s" % (info["version"], major_minor))
        self.assertRegex(info.get("commit", ""), r"^[0-9a-f]{40}$")
        if os.environ.get("GITHUB_SHA"):
            self.assertEqual(info["commit"], os.environ["GITHUB_SHA"])

    def test_scripts_compile(self):
        for name in self.names:
            if name.endswith(".py"):
                with open(os.path.join(self.tmp, name), encoding="utf-8") as f:
                    compile(f.read(), name, "exec")


class CheckModeTests(ArtifactTestCase):
    def test_shipped_readme_has_valid_markers(self):
        r = self.run_app("--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Markers OK", r.stdout)

    def test_broken_readme_is_rejected(self):
        broken = os.path.join(self.tmp, "broken.md")
        with open(broken, "w") as f:
            f.write("# no markers here\n")
        r = self.run_app("--check", "--readme", broken)
        self.assertEqual(r.returncode, 1)
        self.assertIn("::error", r.stdout)


class FakeApiTests(ArtifactTestCase):
    """Runs the shipped script end to end against the fake API."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeGitHub)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.api = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        super().tearDownClass()

    def setUp(self):
        FakeGitHub.seen = []
        FakeGitHub.fail_next = 0
        self.work = tempfile.mkdtemp(prefix="run-", dir=self.tmp)
        self.readme = os.path.join(self.work, "README.md")
        shutil.copy(os.path.join(self.tmp, "README.md"), self.readme)
        self.env = {"GITHUB_TOKEN": "fake-token", "GITHUB_REPOSITORY": REPO, "GITHUB_API_URL": self.api,
                    "CACHE_DIR": os.path.join(self.work, ".cache"),
                    "METRICS_PATH": os.path.join(self.work, "metrics.json"),
                    "MAX_WAIT": "0", "BACKOFF_BASE": "0"}

    def metrics(self):
        with open(self.env["METRICS_PATH"]) as f:
            return json.load(f)

    def test_rewrites_only_the_activity_block(self):
        with open(self.readme) as f:
            before = f.read()
        r = self.run_app("--readme", self.readme, env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(self.readme) as f:
            after = f.read()

        start, end = "<!-- ACTIVITY:START -->", "<!-- ACTIVITY:END -->"
        self.assertEqual(before.split(start)[0], after.split(start)[0], "text above the block changed")
        self.assertEqual(before.split(end)[1], after.split(end)[1], "text below the block changed")
        block = after.split(start)[1].split(end)[0]
        self.assertIn("Add integration tests", block)
        self.assertIn("&lt;script> \\[x\\] escaping", block)       # escaped, cannot inject HTML/links
        self.assertNotIn("chore(readme)", block)                   # bot commits filtered out
        self.assertIn("#21 Test gates", block)
        self.assertNotIn("Closed without merge", block)            # unmerged PRs filtered out
        self.assertIn("#19 Flaky build", block)
        self.assertNotIn("https://x/21", block)                    # PRs are not listed as issues

    def test_sends_token_and_reuses_etag_cache(self):
        self.assertEqual(self.run_app("--readme", self.readme, env=self.env).returncode, 0)
        self.assertEqual(self.metrics()["api_calls"], 3)
        self.assertTrue(all(auth == "Bearer fake-token" for _, _, auth in FakeGitHub.seen))

        FakeGitHub.seen = []
        r = self.run_app("--readme", self.readme, env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("No changes", r.stdout)
        self.assertEqual(self.metrics()["cache_hits"], 3)
        self.assertTrue(all(etag for _, etag, _ in FakeGitHub.seen), "second run did not send If-None-Match")

    def test_retries_after_429(self):
        FakeGitHub.fail_next = 2
        r = self.run_app("--readme", self.readme, env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("HTTP 429, retry 1/", r.stdout)
        self.assertEqual(self.metrics()["retries"], 2)

    def test_gives_up_without_leaking_the_token(self):
        FakeGitHub.fail_next = 99
        env = dict(self.env, MAX_RETRIES="1")
        r = self.run_app("--readme", self.readme, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("failed: HTTP 429", r.stdout + r.stderr)
        self.assertNotIn("fake-token", r.stdout + r.stderr)
        self.assertIsNotNone(self.metrics()["error"])

    def test_dry_run_never_writes(self):
        with open(self.readme) as f:
            before = f.read()
        r = self.run_app("--dry-run", "--readme", self.readme, env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("+- 2026-10-20", r.stdout)
        with open(self.readme) as f:
            self.assertEqual(f.read(), before)


@unittest.skipUnless(TEST_ENV == "prod", "promotion check only runs with TEST_ENV=prod")
class PromotionTests(ArtifactTestCase):
    """Before production: the zip must be byte for byte the one staging already released."""

    def test_same_bytes_as_staging(self):
        staging = os.environ.get("STAGING_ZIP")
        if not staging or not os.path.isfile(staging):
            self.fail("TEST_ENV=prod needs STAGING_ZIP (the zip downloaded from the staging release)")
        self.assertEqual(sha256(BUILD_ZIP), sha256(staging))


if __name__ == "__main__":
    unittest.main()
