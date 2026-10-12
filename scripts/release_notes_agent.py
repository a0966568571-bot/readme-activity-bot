"""Release-notes agent that runs on GitHub Models.

The model gets four read-only tools, all implemented here: git_log, git_diff_stat,
git_show and read_file. It can call them a few times, then must answer with JSON that
matches SCHEMA. It has no shell, cannot write files and never sees a token: the
GitHub token is only used by this script to call the Models API.

Every tool argument is checked before git runs, and git is called with an argument
list (no shell), so a model that has been prompt-injected cannot run other commands.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

API_URL = "https://models.github.ai/inference/chat/completions"
MAX_TURNS = 8
MAX_TOOL_OUTPUT = 8000
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "changes", "risks", "reviewer_checks", "suspicious_input"],
    "properties": {
        "summary": {"type": "string"},
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["type", "description", "commits"],
                "properties": {
                    "type": {"type": "string",
                             "enum": ["feature", "fix", "ci", "docs", "test", "chore", "other"]},
                    "description": {"type": "string"},
                    "commits": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "risks": {"type": "array", "items": {"type": "string"}},
        "reviewer_checks": {"type": "array", "items": {"type": "string"}},
        "suspicious_input": {"type": "array", "items": {"type": "string"}},
    },
}


def _tool(name, description, props, required):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": props, "required": required,
                       "additionalProperties": False}}}


TOOLS = [
    _tool("git_log", "One line per commit (short SHA and subject) in a range like A..B.",
          {"range": {"type": "string"}}, ["range"]),
    _tool("git_diff_stat", "Files changed and line counts for a range like A..B.",
          {"range": {"type": "string"}}, ["range"]),
    _tool("git_show", "Full message and diff of one commit.",
          {"sha": {"type": "string"}}, ["sha"]),
    _tool("read_file", "Read a file in the repository at the current commit.",
          {"path": {"type": "string"}}, ["path"]),
]


class ToolError(Exception):
    pass


def check_range(value):
    parts = value.split("..")
    if len(parts) > 2 or not all(REF_RE.match(p) for p in parts):
        raise ToolError("range must look like REF or REF..REF")
    return value


def check_sha(value):
    if not SHA_RE.match(value):
        raise ToolError("sha must be 7-40 lowercase hex characters")
    return value


def check_path(value, root):
    full = os.path.realpath(os.path.join(root, value))
    root = os.path.realpath(root)
    if not full.startswith(root + os.sep):
        raise ToolError("path must stay inside the repository")
    rel = os.path.relpath(full, root)
    if rel == ".git" or rel.startswith(".git" + os.sep):
        raise ToolError(".git is not readable")
    if not os.path.isfile(full):
        raise ToolError("no such file")
    return full


def cut(text):
    if len(text) <= MAX_TOOL_OUTPUT:
        return text
    return text[:MAX_TOOL_OUTPUT] + "\n[cut at %d characters]" % MAX_TOOL_OUTPUT


def git(*args):
    out = subprocess.run(["git"] + list(args), capture_output=True, text=True)
    if out.returncode != 0:
        raise ToolError(out.stderr.strip()[:300])
    return out.stdout


def run_tool(name, args, root="."):
    try:
        if name == "git_log":
            return cut(git("log", "--no-merges", "--format=%h %s", check_range(args["range"]), "--"))
        if name == "git_diff_stat":
            return cut(git("diff", "--stat", check_range(args["range"]), "--"))
        if name == "git_show":
            return cut(git("show", "--stat", "--patch", check_sha(args["sha"]), "--"))
        if name == "read_file":
            with open(check_path(args["path"], root), errors="replace") as f:
                return cut(f.read())
        raise ToolError("unknown tool")
    except (ToolError, KeyError, TypeError) as e:
        return "error: %s" % e


def call_model(token, body):
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode(errors="replace")
                kind = resp.headers.get("Content-Type", "")
            try:
                return json.loads(raw)
            except ValueError:
                raise RuntimeError("Models API returned non-JSON (%s): %r" % (kind, raw[:300])) from None
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError("Models API %d: %s" % (e.code, e.read().decode()[:300])) from None


def run_agent(token, model, system_prompt, user_prompt, trace):
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}]
    fmt = {"type": "json_schema",
           "json_schema": {"name": "release_notes", "strict": True, "schema": SCHEMA}}
    for turn in range(1, MAX_TURNS + 1):
        last = turn == MAX_TURNS
        body = {"model": model, "messages": messages, "response_format": fmt, "temperature": 0.2}
        if not last:
            body["tools"] = TOOLS
        msg = call_model(token, body)["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        if not calls:
            try:
                data = json.loads(msg.get("content") or "")
            except ValueError:
                raise RuntimeError("model answer is not JSON: %r" % (msg.get("content") or "")[:300]) from None
            trace({"turn": turn, "final": True})
            return data
        messages.append({"role": "assistant", "content": msg.get("content"), "tool_calls": calls})
        for call in calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"]["arguments"] or "{}")
            except ValueError:
                args = {}
            result = run_tool(name, args)
            trace({"turn": turn, "tool": name, "args": args, "result_chars": len(result),
                   "error": result.startswith("error:")})
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
    raise RuntimeError("no answer after %d turns" % MAX_TURNS)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--version", required=True)
    p.add_argument("--prev-tag", default="")
    p.add_argument("--range", required=True)
    p.add_argument("--prompt", default=".github/agent/release-notes-prompt.md")
    p.add_argument("--out", default="agent-output.json")
    p.add_argument("--trace", default="agent-trace.jsonl")
    a = p.parse_args()

    with open(a.prompt) as f:
        system_prompt = (f.read().replace("{{VERSION}}", a.version)
                         .replace("{{PREV_TAG}}", a.prev_tag or "none")
                         .replace("{{RANGE}}", a.range))
    model = os.environ.get("MODEL") or "openai/gpt-4.1"
    trace_file = open(a.trace, "w")

    def trace(event):
        print(json.dumps(event))
        trace_file.write(json.dumps(event) + "\n")

    trace({"model": model, "range": a.range})
    data = run_agent(os.environ["GITHUB_TOKEN"], model, system_prompt,
                     "Write the release notes for %s." % a.version, trace)
    with open(a.out, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # the job is continue-on-error; say why and stop
        print("::error::release-notes agent failed: %s" % e)
        sys.exit(1)
