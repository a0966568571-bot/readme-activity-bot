#!/usr/bin/env python3
"""Rewrite the Recent Activity block in README.md from GitHub API data.

Modes:
  (default)    write README.md only if the block changed
  --dry-run    show what would change, never write
  --check      only validate the markers (no API calls, no token needed)

Settings come from environment variables so CI can tune them without code changes:
  GITHUB_TOKEN, GITHUB_REPOSITORY      required unless --check
  ITEM_LIMIT      items per list                  (default 5)
  MAX_RETRIES     retries per request             (default 4)
  BACKOFF_BASE    exponential backoff base, sec   (default 2)
  MAX_WAIT        cap for a single wait, sec      (default 60)
  CACHE_DIR       where the ETag cache lives      (default .cache)
  METRICS_PATH    where run metrics are written   (default metrics.json)
  SIMULATE_STATUS / SIMULATE_COUNT   fake N failed responses (e.g. 429) to test backoff

Uses only the Python standard library, so CI needs no pip install.
"""
import argparse
import difflib
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

START = "<!-- ACTIVITY:START -->"
END = "<!-- ACTIVITY:END -->"
NOTE = "_Updated automatically by GitHub Actions. Do not edit this block by hand._"
BOT_COMMIT_PREFIX = "chore(readme):"
BOT_LOGINS = {"github-actions[bot]"}
API = "https://api.github.com"
RETRY_STATUS = {429, 500, 502, 503, 504}


# ---------- markers ----------

def _marker_lines(text, marker):
    # A marker counts only when it sits alone on its own line, so prose that
    # mentions `<!-- ACTIVITY:START -->` inside a sentence is not mistaken for one.
    return [i for i, line in enumerate(text.splitlines()) if line.strip() == marker]


def check_markers(text):
    """Return a list of problems with the markers; empty list means OK."""
    errors = []
    starts, ends = _marker_lines(text, START), _marker_lines(text, END)
    if len(starts) != 1:
        errors.append("expected exactly 1 %s line, found %d" % (START, len(starts)))
    if len(ends) != 1:
        errors.append("expected exactly 1 %s line, found %d" % (END, len(ends)))
    if len(starts) == 1 and len(ends) == 1 and starts[0] > ends[0]:
        errors.append("%s must come before %s" % (START, END))
    return errors


def replace_block(text, body):
    """Replace only the lines between the markers; keep everything else byte for byte."""
    lines = text.splitlines(True)
    s, e = _marker_lines(text, START)[0], _marker_lines(text, END)[0]
    return "".join(lines[:s + 1]) + body + "\n" + "".join(lines[e:])


# ---------- HTTP with retry, backoff and ETag cache ----------

class Config(object):
    def __init__(self, env):
        self.item_limit = int(env.get("ITEM_LIMIT", "5"))
        self.max_retries = int(env.get("MAX_RETRIES", "4"))
        self.backoff_base = float(env.get("BACKOFF_BASE", "2"))
        self.max_wait = float(env.get("MAX_WAIT", "60"))
        self.cache_dir = env.get("CACHE_DIR", ".cache")
        self.metrics_path = env.get("METRICS_PATH", "metrics.json")
        self.simulate_status = int(env.get("SIMULATE_STATUS", "0") or 0)
        self.simulate_left = int(env.get("SIMULATE_COUNT", "0") or 0)


def new_metrics():
    return {
        "api_calls": 0,            # real requests sent to GitHub
        "cache_hits": 0,           # 304 Not Modified answers (free: not counted by the rate limit)
        "retries": 0,
        "wait_seconds": 0.0,
        "simulated_failures": 0,
        "rate_limit_remaining": None,
    }


def backoff_delay(attempt, headers, cfg, now=None):
    """How long to wait before retry number `attempt` (0-based).

    Order of preference: the server's Retry-After, then the rate-limit reset time,
    then exponential backoff with jitter. Never longer than MAX_WAIT.
    """
    now = time.time() if now is None else now
    retry_after = headers.get("retry-after")
    if retry_after and retry_after.isdigit():
        return min(float(retry_after), cfg.max_wait)
    reset = headers.get("x-ratelimit-reset")
    if headers.get("x-ratelimit-remaining") == "0" and reset and reset.isdigit():
        return min(max(0.0, int(reset) - now) + 1, cfg.max_wait)
    return min(cfg.backoff_base ** attempt + random.uniform(0, 1), cfg.max_wait)


def is_retryable(status, headers, body):
    if status in RETRY_STATUS:
        return True
    # 403 is retried only when it is a rate limit, not a permission problem.
    if status == 403:
        return headers.get("x-ratelimit-remaining") == "0" or b"rate limit" in body.lower()
    return False


def _send(url, headers, cfg, metrics):
    """One HTTP GET. Returns (status, lower-cased headers, body bytes)."""
    if cfg.simulate_left > 0:
        cfg.simulate_left -= 1
        metrics["simulated_failures"] += 1
        return cfg.simulate_status, {}, b""
    metrics["api_calls"] += 1
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
    except urllib.error.URLError:
        return 0, {}, b""


def fetch_json(path, token, cache, cfg, metrics, sleep=time.sleep):
    url = API + path
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "readme-activity-bot",
    }
    cached = cache.get(url)
    if cached:
        headers["If-None-Match"] = cached["etag"]

    for attempt in range(cfg.max_retries + 1):
        status, resp_headers, body = _send(url, headers, cfg, metrics)
        if "x-ratelimit-remaining" in resp_headers:
            metrics["rate_limit_remaining"] = int(resp_headers["x-ratelimit-remaining"])

        if status == 304 and cached:
            metrics["cache_hits"] += 1
            return cached["data"]
        if status == 200:
            data = json.loads(body.decode("utf-8"))
            if resp_headers.get("etag"):
                cache[url] = {"etag": resp_headers["etag"], "data": data}
            return data

        retryable = status == 0 or is_retryable(status, resp_headers, body)
        if not retryable or attempt == cfg.max_retries:
            # Only the status and path are printed: never headers or bodies.
            raise SystemExit("GET %s failed: HTTP %s" % (path, status or "network error"))
        wait = backoff_delay(attempt, resp_headers, cfg)
        metrics["retries"] += 1
        metrics["wait_seconds"] += wait
        print("GET %s -> HTTP %s, retry %d/%d in %.1fs"
              % (path, status or "network error", attempt + 1, cfg.max_retries, wait))
        sleep(wait)


def load_cache(cfg):
    try:
        with open(os.path.join(cfg.cache_dir, "etag-cache.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_cache(cfg, cache):
    os.makedirs(cfg.cache_dir, exist_ok=True)
    with open(os.path.join(cfg.cache_dir, "etag-cache.json"), "w") as f:
        json.dump(cache, f)


# ---------- data and rendering ----------

def is_bot_commit(c):
    message = c["commit"]["message"]
    login = (c.get("author") or {}).get("login", "")
    return message.startswith(BOT_COMMIT_PREFIX) or login in BOT_LOGINS


def collect(repo, token, cache, cfg, metrics):
    base = "/repos/" + repo
    commits = fetch_json(base + "/commits?per_page=30", token, cache, cfg, metrics)
    pulls = fetch_json(base + "/pulls?state=closed&sort=updated&direction=desc&per_page=30",
                       token, cache, cfg, metrics)
    issues = fetch_json(base + "/issues?state=closed&sort=updated&direction=desc&per_page=30",
                        token, cache, cfg, metrics)
    n = cfg.item_limit
    commits = [c for c in commits if not is_bot_commit(c)][:n]
    pulls = sorted([p for p in pulls if p.get("merged_at")],
                   key=lambda p: p["merged_at"], reverse=True)[:n]
    issues = sorted([i for i in issues if "pull_request" not in i],
                    key=lambda i: i["closed_at"], reverse=True)[:n]
    return commits, pulls, issues


def _esc(s):
    return s.replace("<", "&lt;").replace("[", "\\[").replace("]", "\\]")


def _who(c):
    return (c.get("author") or {}).get("login") or c["commit"]["author"]["name"]


def render(commits, pulls, issues):
    """Deterministic output: same data in, same text out. No timestamps of the run itself."""
    out = [NOTE, "", "**Latest commits**", ""]
    out += ["- %s [`%s`](%s) %s, by %s" % (c["commit"]["author"]["date"][:10], c["sha"][:7],
                                          c["html_url"], _esc(c["commit"]["message"].splitlines()[0]),
                                          _who(c)) for c in commits] or ["- _None yet._"]
    out += ["", "**Recently merged pull requests**", ""]
    out += ["- %s [#%d %s](%s), by %s" % (p["merged_at"][:10], p["number"], _esc(p["title"]),
                                          p["html_url"], p["user"]["login"]) for p in pulls] or ["- _None yet._"]
    out += ["", "**Recently closed issues**", ""]
    out += ["- %s [#%d %s](%s)" % (i["closed_at"][:10], i["number"], _esc(i["title"]),
                                   i["html_url"]) for i in issues] or ["- _None yet._"]
    return "\n".join(out)


# ---------- reporting ----------

def write_outputs(metrics, diff_text):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write("changed=%s\n" % str(metrics["changed"]).lower())
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        rows = ["| Metric | Value |", "|---|---|"]
        rows += ["| %s | %s |" % (k, v) for k, v in metrics.items()]
        with open(summary, "a") as f:
            f.write("### README update run\n\n" + "\n".join(rows) + "\n")
            if diff_text:
                f.write("\n<details><summary>README diff</summary>\n\n```diff\n%s\n```\n</details>\n" % diff_text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="validate markers only")
    group.add_argument("--dry-run", action="store_true", help="show the diff, do not write")
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--diff-out", help="also save the diff to this file")
    args = parser.parse_args(argv)

    with open(args.readme, encoding="utf-8") as f:
        text = f.read()
    errors = check_markers(text)
    if errors:
        for e in errors:
            print("::error file=%s::%s" % (args.readme, e))
        return 1
    if args.check:
        print("Markers OK in %s" % args.readme)
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("GITHUB_TOKEN and GITHUB_REPOSITORY must be set")
        return 2

    cfg = Config(os.environ)
    metrics = new_metrics()
    started = time.time()
    cache = load_cache(cfg)

    new_text = replace_block(text, render(*collect(repo, token, cache, cfg, metrics)))
    changed = new_text != text
    diff_text = "".join(difflib.unified_diff(text.splitlines(True), new_text.splitlines(True),
                                             "README.md (current)", "README.md (updated)"))
    if args.dry_run:
        print(diff_text or "No changes.")
    elif changed:
        with open(args.readme, "w", encoding="utf-8") as f:
            f.write(new_text)
        print("README.md updated.")
    else:
        print("No changes, README.md left as is.")
    if args.diff_out:
        with open(args.diff_out, "w", encoding="utf-8") as f:
            f.write(diff_text)
    save_cache(cfg, cache)

    metrics.update({
        "mode": "dry-run" if args.dry_run else "write",
        "changed": changed,
        "duration_seconds": round(time.time() - started, 2),
        "wait_seconds": round(metrics["wait_seconds"], 2),
        "event": os.environ.get("GITHUB_EVENT_NAME", "local"),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "finished_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    with open(cfg.metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    write_outputs(metrics, diff_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
