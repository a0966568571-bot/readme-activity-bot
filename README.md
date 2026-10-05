# readme-activity-bot

This README keeps its own **Recent Activity** section up to date.
A GitHub Actions workflow reads the latest commits, merged pull requests and closed issues from the GitHub REST API, then rewrites only the block between the two markers below.

## Recent Activity

<!-- ACTIVITY:START -->
_Updated automatically by GitHub Actions. Do not edit this block by hand._
<!-- ACTIVITY:END -->

## How it works

1. `.github/workflows/update-readme.yml` runs on a schedule, on manual dispatch and on pushes to `main`.
2. `scripts/update_readme.py` fetches recent activity and renders it as Markdown.
3. Only the text between `<!-- ACTIVITY:START -->` and `<!-- ACTIVITY:END -->` is replaced. Everything else in this file is left alone.
4. If the new block is identical to the old one, nothing is committed.

## Project tracking

Work is tracked on the [README Automation board](https://github.com/users/a0966568571-bot/projects/2).

- #1 Automate the Recent Activity section
- #2 CI guardrails and run reporting
