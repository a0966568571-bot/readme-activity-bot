import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import update_readme as u  # noqa: E402

README = "# Title\n\nIntro\n\n%s\nold\n%s\n\n## Footer\n" % (u.START, u.END)


def commit(sha, message, login="alice", date="2026-10-05T10:00:00Z"):
    return {"sha": sha, "html_url": "https://x/" + sha, "author": {"login": login},
            "commit": {"message": message, "author": {"name": login, "date": date}}}


class MarkerTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(u.check_markers(README), [])

    def test_missing_end(self):
        self.assertEqual(len(u.check_markers(README.replace(u.END, ""))), 1)

    def test_duplicated_start(self):
        self.assertTrue(u.check_markers(README + u.START))

    def test_marker_mentioned_in_prose_is_ignored(self):
        doc = README + "\nThe block starts at `%s` and ends at `%s`.\n" % (u.START, u.END)
        self.assertEqual(u.check_markers(doc), [])
        self.assertIn("ends at `%s`" % u.END, u.replace_block(doc, "new"))

    def test_wrong_order(self):
        swapped = "%s\n%s\n" % (u.END, u.START)
        self.assertIn("must come before", u.check_markers(swapped)[0])


class ReplaceTests(unittest.TestCase):
    def test_only_block_changes(self):
        new = u.replace_block(README, "new")
        self.assertTrue(new.startswith("# Title\n\nIntro\n\n"))
        self.assertTrue(new.endswith("\n\n## Footer\n"))
        self.assertIn(u.START + "\nnew\n" + u.END, new)

    def test_idempotent(self):
        once = u.replace_block(README, "same")
        self.assertEqual(once, u.replace_block(once, "same"))


class RenderTests(unittest.TestCase):
    def test_bot_commits_are_skipped(self):
        self.assertTrue(u.is_bot_commit(commit("a", "chore(readme): update recent activity")))
        self.assertTrue(u.is_bot_commit(commit("b", "anything", login="github-actions[bot]")))
        self.assertFalse(u.is_bot_commit(commit("c", "Add feature")))

    def test_empty_lists(self):
        self.assertEqual(u.render([], [], []).count("_None yet._"), 3)

    def test_deterministic_and_escaped(self):
        commits = [commit("abcdef123", "Fix [link] <b>\n\nbody")]
        out = u.render(commits, [], [])
        self.assertEqual(out, u.render(commits, [], []))
        self.assertIn("Fix \\[link\\] &lt;b>", out)
        self.assertNotIn("body", out)


class BackoffTests(unittest.TestCase):
    def setUp(self):
        self.cfg = u.Config({"BACKOFF_BASE": "2", "MAX_WAIT": "60"})

    def test_retry_after_wins(self):
        self.assertEqual(u.backoff_delay(3, {"retry-after": "7"}, self.cfg), 7)

    def test_rate_limit_reset(self):
        h = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1010"}
        self.assertEqual(u.backoff_delay(0, h, self.cfg, now=1000), 11)

    def test_exponential_and_capped(self):
        self.assertTrue(4 <= u.backoff_delay(2, {}, self.cfg) < 5)
        self.assertEqual(u.backoff_delay(10, {}, self.cfg), 60)

    def test_403_permission_is_not_retried(self):
        self.assertFalse(u.is_retryable(403, {"x-ratelimit-remaining": "4000"}, b"Resource not accessible"))
        self.assertTrue(u.is_retryable(403, {"x-ratelimit-remaining": "0"}, b""))
        self.assertTrue(u.is_retryable(429, {}, b""))


class FetchTests(unittest.TestCase):
    def test_simulated_429_then_gives_up(self):
        cfg = u.Config({"MAX_RETRIES": "2", "SIMULATE_STATUS": "429", "SIMULATE_COUNT": "9"})
        metrics, waits = u.new_metrics(), []
        with self.assertRaises(SystemExit) as ctx:
            u.fetch_json("/x", "secret-token", {}, cfg, metrics, sleep=waits.append)
        self.assertEqual(metrics["retries"], 2)
        self.assertEqual(len(waits), 2)
        self.assertNotIn("secret-token", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
