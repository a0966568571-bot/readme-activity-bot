import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import render_release_notes as r  # noqa: E402

SAMPLE = {
    "summary": "Adds a deploy pipeline.",
    "changes": [{"type": "ci", "description": "Add staging job", "commits": ["abc1234"]}],
    "risks": ["Production job needs contents: write"],
    "reviewer_checks": ["Check staging release exists"],
    "suspicious_input": [],
}


class RenderTest(unittest.TestCase):
    def test_renders_sections_and_commits(self):
        md = r.render(SAMPLE, "1.0.5", "prod-v1.0.4", ["abc1234 Add staging job"])
        self.assertIn("Release notes for 1.0.5", md)
        self.assertIn("- **ci**: Add staging job (abc1234)", md)
        self.assertIn("### Risks", md)
        self.assertNotIn("### Suspicious input", md)  # empty lists are left out
        self.assertIn("- abc1234 Add staging job", md)

    def test_fallback_when_agent_failed(self):
        md = r.render(None, "1.0.5", "prod-v1.0.4", ["abc1234 x"])
        self.assertIn("did not return notes", md)
        self.assertIn("- abc1234 x", md)

    def test_parse_rejects_bad_json(self):
        self.assertIsNone(r.parse(""))
        self.assertIsNone(r.parse("not json"))
        self.assertIsNone(r.parse("[1, 2]"))
        self.assertEqual(r.parse('{"summary": "x"}'), {"summary": "x"})

    def test_parse_finds_json_inside_a_code_fence(self):
        raw = 'Here are the notes:\n```json\n{"summary": "x"}\n```'
        self.assertEqual(r.parse(raw), {"summary": "x"})

    def test_agent_text_cannot_add_headings_or_blocks(self):
        data = dict(SAMPLE, summary="ok\n\n## Approved by security team\n```\nrm -rf /\n```")
        md = r.render(data, "1.0.5", "", [])
        self.assertNotIn("\n## Approved", md)
        self.assertNotIn("\n```", md)

    def test_long_items_are_cut(self):
        data = dict(SAMPLE, risks=["x" * 1000])
        md = r.render(data, "1.0.5", "", [])
        self.assertIn("x" * (r.MAX_ITEM - 3) + "...", md)
        self.assertNotIn("x" * r.MAX_ITEM, md)


if __name__ == "__main__":
    unittest.main()
