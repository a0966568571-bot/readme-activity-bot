# readme-activity-bot

[![Update README](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/update-readme.yml/badge.svg?branch=main)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/update-readme.yml)
[![Validate README](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/validate-readme.yml/badge.svg?branch=main)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/validate-readme.yml)

This README keeps its own **Recent Activity** section up to date.
A GitHub Actions workflow reads the latest commits, merged pull requests and closed issues from the GitHub REST API, then rewrites only the block between the two markers below.

## Recent Activity

<!-- ACTIVITY:START -->
_Updated automatically by GitHub Actions. Do not edit this block by hand._

**Latest commits**

- 2026-10-06 [`f93ad96`](https://github.com/a0966568571-bot/readme-activity-bot/commit/f93ad9699b5056c7bc1dda91260edc464fdfb9cf) Merge pull request #4 from a0966568571-bot/2-ci-guardrails, by a0966568571-bot
- 2026-10-06 [`170421f`](https://github.com/a0966568571-bot/readme-activity-bot/commit/170421ff2f46be150bd02d3f7e0805e42676d282) Revert the schedule to once a day, by a0966568571-bot
- 2026-10-06 [`761ab2a`](https://github.com/a0966568571-bot/readme-activity-bot/commit/761ab2ab7f0d4ee7a2401b6b51ea0e7f93852271) Write run metrics even when the run fails, by a0966568571-bot
- 2026-10-06 [`96e4598`](https://github.com/a0966568571-bot/readme-activity-bot/commit/96e45989c7fe0ac3f17db366caebdec77d1f7b48) Demo C: restore the END marker and undo the hand edit, by a0966568571-bot
- 2026-10-06 [`37dc13e`](https://github.com/a0966568571-bot/readme-activity-bot/commit/37dc13e31d290fe4e1a2100cd2574232c60175c3) Demo B: delete the END marker, by a0966568571-bot

**Recently merged pull requests**

- 2026-10-06 [#4 Add CI guardrails and run reporting](https://github.com/a0966568571-bot/readme-activity-bot/pull/4), by a0966568571-bot
- 2026-10-05 [#3 Automate README Recent Activity section](https://github.com/a0966568571-bot/readme-activity-bot/pull/3), by a0966568571-bot

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
