# readme-activity-bot

[![Update README](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/update-readme.yml/badge.svg?branch=main)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/update-readme.yml)
[![Validate README](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/validate-readme.yml/badge.svg?branch=main)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/validate-readme.yml)

This README keeps its own **Recent Activity** section up to date.
A GitHub Actions workflow reads the latest commits, merged pull requests and closed issues from the GitHub REST API, then rewrites only the block between the two markers below.

## Recent Activity

<!-- ACTIVITY:START -->
_Updated automatically by GitHub Actions. Do not edit this block by hand._

**Latest commits**

- 2026-10-12 [`e161668`](https://github.com/a0966568571-bot/readme-activity-bot/commit/e161668cb1dad371c321d0186f888dbcaadb09e3) Merge pull request #11 from a0966568571-bot/agent-error-summary, by a0966568571-bot
- 2026-10-12 [`03c6490`](https://github.com/a0966568571-bot/readme-activity-bot/commit/03c649093ba56440923a5edc5e9a93b2d90b6fde) Print the agent's final result line so failures show a reason, by a0966568571-bot
- 2026-10-12 [`85a85e7`](https://github.com/a0966568571-bot/readme-activity-bot/commit/85a85e79e8b59c05cbf7487f060bd695b933fb2b) Merge pull request #10 from a0966568571-bot/fix-agent-action, by a0966568571-bot
- 2026-10-12 [`f138916`](https://github.com/a0966568571-bot/readme-activity-bot/commit/f138916ca5032829d5f6e1e3aff0a9039ef75ff7) Use maintained base-action; the old repo installs Claude Code 1.0.88, by a0966568571-bot
- 2026-10-12 [`4d5f5ff`](https://github.com/a0966568571-bot/readme-activity-bot/commit/4d5f5ffeca2acf3e7ad163bdfeac731e5cb154ff) Merge pull request #9 from a0966568571-bot/ai-release-notes, by a0966568571-bot

**Recently merged pull requests**

- 2026-10-12 [#11 Show the agent's result line in the log](https://github.com/a0966568571-bot/readme-activity-bot/pull/11), by a0966568571-bot
- 2026-10-12 [#10 Fix release-notes agent: use maintained base-action](https://github.com/a0966568571-bot/readme-activity-bot/pull/10), by a0966568571-bot
- 2026-10-12 [#9 AI release-notes agent before production approval](https://github.com/a0966568571-bot/readme-activity-bot/pull/9), by a0966568571-bot
- 2026-10-11 [#8 Pipeline automation: lint/test gate, semver auto-bump, rollback, notifications](https://github.com/a0966568571-bot/readme-activity-bot/pull/8), by a0966568571-bot
- 2026-10-11 [#6 Deployment pipeline: staging + production with approval](https://github.com/a0966568571-bot/readme-activity-bot/pull/6), by a0966568571-bot

**Recently closed issues**

- 2026-10-06 [#2 Add CI guardrails and run reporting for README automation](https://github.com/a0966568571-bot/readme-activity-bot/issues/2)
- 2026-10-05 [#1 Automate README "Recent Activity" section with GitHub Actions](https://github.com/a0966568571-bot/readme-activity-bot/issues/1)
<!-- ACTIVITY:END -->

## How it works

1. `.github/workflows/update-readme.yml` runs on a schedule, on manual dispatch and on pushes to `main`.
2. `scripts/update_readme.py` fetches recent activity and renders it as Markdown.
3. Only the text between `<!-- ACTIVITY:START -->` and `<!-- ACTIVITY:END -->` is replaced. Everything else in this file is left alone.
4. If the new block is identical to the old one, nothing is committed.

## Guardrails

| Workflow | When | What it does |
|---|---|---|
| `validate-readme.yml` | every PR and push to `main` | fails if the markers are missing, duplicated or out of order; runs unit tests on Python 3.9 and 3.13 |
| `readme-preview.yml` | every PR | dry run, then posts the README diff as one PR comment that is updated on each push |
| `metrics-report.yml` | manual | collects `metrics.json` from past runs into one report |

API calls retry with exponential backoff on 429/5xx and on rate-limit 403s. Settings live in repository variables (`MAX_RETRIES`, `BACKOFF_BASE`, `MAX_WAIT`). A manual run can fake failures to test this (`simulate_status`, `simulate_count`).

## Project tracking

Work is tracked on the [README Automation board](https://github.com/users/a0966568571-bot/projects/2).

- #1 Automate the Recent Activity section
- #2 CI guardrails and run reporting
