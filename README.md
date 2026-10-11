# readme-activity-bot

[![Update README](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/update-readme.yml/badge.svg?branch=main)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/update-readme.yml)
[![Validate README](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/validate-readme.yml/badge.svg?branch=main)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/validate-readme.yml)

This README keeps its own **Recent Activity** section up to date.
A GitHub Actions workflow reads the latest commits, merged pull requests and closed issues from the GitHub REST API, then rewrites only the block between the two markers below.

## Recent Activity

<!-- ACTIVITY:START -->
_Updated automatically by GitHub Actions. Do not edit this block by hand._

**Latest commits**

- 2026-10-11 [`a429651`](https://github.com/a0966568571-bot/readme-activity-bot/commit/a42965146661f86ba45796110be660ea5a52a6f0) Merge pull request #8 from a0966568571-bot/pipeline-automation, by a0966568571-bot
- 2026-10-11 [`d3557c0`](https://github.com/a0966568571-bot/readme-activity-bot/commit/d3557c03e4711fdb3c3e195b61c4bb58125b692a) Add lint, test matrix, auto version, smoke test with rollback, release notifications, by a0966568571-bot
- 2026-10-11 [`2ca778b`](https://github.com/a0966568571-bot/readme-activity-bot/commit/2ca778b7bbf2d8f147d0142a5c533ff46c7f967f) Merge pull request #6 from a0966568571-bot/deploy-staging-prod, by a0966568571-bot
- 2026-10-11 [`622ea30`](https://github.com/a0966568571-bot/readme-activity-bot/commit/622ea302652ee5ba3b890b62b31a47b8ed14c0e6) Add staging and production deploy jobs, by a0966568571-bot
- 2026-10-11 [`3913480`](https://github.com/a0966568571-bot/readme-activity-bot/commit/3913480b41fe292a6a1c066a56574c3a97e39cc5) Merge pull request #5 from a0966568571-bot/deploy-pipeline, by a0966568571-bot

**Recently merged pull requests**

- 2026-10-11 [#8 Pipeline automation: lint/test gate, semver auto-bump, rollback, notifications](https://github.com/a0966568571-bot/readme-activity-bot/pull/8), by a0966568571-bot
- 2026-10-11 [#6 Deployment pipeline: staging + production with approval](https://github.com/a0966568571-bot/readme-activity-bot/pull/6), by a0966568571-bot
- 2026-10-11 [#5 Deployment pipeline: build + dev release](https://github.com/a0966568571-bot/readme-activity-bot/pull/5), by a0966568571-bot
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
