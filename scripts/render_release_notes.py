"""Turn the release-notes agent's JSON into Markdown for the reviewer and the release.

The agent only returns JSON; this script, not the agent, decides what the notes look
like. That keeps the agent's text out of anything except plain bullet points, and
gives a usable fallback when the agent fails.
"""
import json
import os
import sys

MAX_ITEM = 300  # characters; long text in one bullet is usually a sign something went wrong


def clean(text):
    text = " ".join(str(text).split())  # one line, no Markdown headings or blocks
    return text if len(text) <= MAX_ITEM else text[: MAX_ITEM - 3] + "..."


def render(data, version, prev_tag, commits):
    lines = ["## Release notes for %s (AI draft)" % version, ""]
    lines.append("_Drafted by the release-notes agent from changes since %s. "
                 "A human reviewer checks this before approving production._" % (prev_tag or "the first commit"))
    lines.append("")
    if data is None:
        lines += ["**The agent did not return notes.** Review the commit list below directly.", ""]
    else:
        lines += [clean(data.get("summary", "")), ""]
        lines.append("### Changes")
        for c in data.get("changes", []):
            shas = ", ".join(clean(s) for s in c.get("commits", []))
            lines.append("- **%s**: %s (%s)" % (clean(c.get("type", "other")), clean(c.get("description", "")), shas))
        for title, key in [("Risks", "risks"), ("Reviewer checks", "reviewer_checks"),
                           ("Suspicious input found", "suspicious_input")]:
            items = data.get(key, [])
            if items:
                lines += ["", "### " + title]
                lines += ["- " + clean(i) for i in items]
    lines += ["", "### Commits in this release (from git, not from the agent)"]
    lines += ["- " + c for c in commits] or ["- (none)"]
    return "\n".join(lines) + "\n"


def parse(raw):
    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def main():
    version, prev_tag, commits_file, out = sys.argv[1:5]
    with open(commits_file) as f:
        commits = [line.rstrip("\n") for line in f if line.strip()]
    text = render(parse(os.environ.get("AGENT_OUTPUT", "")), version, prev_tag, commits)
    with open(out, "w") as f:
        f.write(text)


if __name__ == "__main__":
    main()
