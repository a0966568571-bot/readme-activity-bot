import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import release_notes_agent as a  # noqa: E402


class ToolGuardTest(unittest.TestCase):
    def test_range_accepts_tags_and_shas(self):
        for ok in ["prod-v1.0.4..abc1234", "HEAD", "prod-v1.0.4..e7426f2deadbeef"]:
            self.assertEqual(a.check_range(ok), ok)

    def test_range_rejects_options_and_shell(self):
        for bad in ["--output=/tmp/x", "-p", "a..b..c", "HEAD; rm -rf /", "$(id)", "a b", ""]:
            with self.assertRaises(a.ToolError):
                a.check_range(bad)

    def test_sha(self):
        a.check_sha("abc1234")
        for bad in ["ABC1234", "abc", "--all", "abc1234 --stat"]:
            with self.assertRaises(a.ToolError):
                a.check_sha(bad)

    def test_path_stays_in_repo_and_out_of_git(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".git"))
            open(os.path.join(root, ".git", "config"), "w").close()
            open(os.path.join(root, "README.md"), "w").close()
            self.assertTrue(a.check_path("README.md", root).endswith("README.md"))
            for bad in ["../etc/passwd", "/etc/passwd", ".git/config", "missing.txt"]:
                with self.assertRaises(a.ToolError):
                    a.check_path(bad, root)

    def test_bad_tool_calls_return_errors_not_exceptions(self):
        self.assertTrue(a.run_tool("git_log", {"range": "--all"}).startswith("error:"))
        self.assertTrue(a.run_tool("bash", {"cmd": "id"}).startswith("error:"))
        self.assertTrue(a.run_tool("git_show", {}).startswith("error:"))

    def test_long_output_is_cut(self):
        self.assertTrue(a.cut("x" * (a.MAX_TOOL_OUTPUT + 10)).endswith("characters]"))


class AgentLoopTest(unittest.TestCase):
    def test_runs_tools_then_returns_json(self):
        replies = [
            {"choices": [{"message": {"content": None, "tool_calls": [
                {"id": "1", "function": {"name": "git_log", "arguments": '{"range": "--all"}'}}]}}]},
            {"choices": [{"message": {"content": '{"summary": "s", "changes": [], "risks": [],'
                                                 ' "reviewer_checks": [], "suspicious_input": []}'}}]},
        ]
        events = []
        with mock.patch.object(a, "call_model", side_effect=replies) as call:
            data = a.run_agent("t", "m", "sys", "user", events.append)
        self.assertEqual(data["summary"], "s")
        self.assertTrue(events[0]["error"])  # the bad range was refused
        tool_msg = call.call_args_list[1][0][1]["messages"][-1]
        self.assertEqual(tool_msg["role"], "tool")

    def test_last_turn_offers_no_tools(self):
        loop = {"choices": [{"message": {"content": None, "tool_calls": [
            {"id": "1", "function": {"name": "git_log", "arguments": '{"range": "HEAD"}'}}]}}]}
        final = {"choices": [{"message": {"content": "{}"}}]}
        replies = [loop] * (a.MAX_TURNS - 1) + [final]
        with mock.patch.object(a, "call_model", side_effect=replies) as call, \
                mock.patch.object(a, "run_tool", return_value="ok"):
            a.run_agent("t", "m", "sys", "user", lambda e: None)
        self.assertNotIn("tools", call.call_args_list[-1][0][1])


if __name__ == "__main__":
    unittest.main()
