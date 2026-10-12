# readme-activity-bot

[![Update README](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/update-readme.yml/badge.svg?branch=main)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/update-readme.yml)
[![Validate README](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/validate-readme.yml/badge.svg?branch=main)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/validate-readme.yml)

This README keeps its own **Recent Activity** section up to date.
A GitHub Actions workflow reads the latest commits, merged pull requests and closed issues from the GitHub REST API, then rewrites only the block between the two markers below.

## Recent Activity

<!-- ACTIVITY:START -->
_Updated automatically by GitHub Actions. Do not edit this block by hand._

**Latest commits**

- 2026-10-12 [`b1a96c2`](https://github.com/a0966568571-bot/readme-activity-bot/commit/b1a96c2e17dceebfc3d9d5203cf5c47124e77314) Merge pull request #16 from a0966568571-bot/notes-visible-before-approval, by a0966568571-bot
- 2026-10-12 [`443356d`](https://github.com/a0966568571-bot/readme-activity-bot/commit/443356d871ab4c5f0195b52c1761ae35aa3e0eef) Show the AI draft to the reviewer while production is waiting, by a0966568571-bot
- 2026-10-12 [`f5c5e76`](https://github.com/a0966568571-bot/readme-activity-bot/commit/f5c5e76094937b8c603865fe01cf48e9f0551751) Merge pull request #15 from a0966568571-bot/pin-copilot-and-docs, by a0966568571-bot
- 2026-10-12 [`8af681f`](https://github.com/a0966568571-bot/readme-activity-bot/commit/8af681f5f4619178346f9cfb41a211b27c448e13) docs: describe the deployment pipeline in README, by a0966568571-bot
- 2026-10-12 [`5de2fbd`](https://github.com/a0966568571-bot/readme-activity-bot/commit/5de2fbde3708278ea20f21ca036a70d416f73c19) Pin Copilot CLI to 1.0.96, by a0966568571-bot

**Recently merged pull requests**

- 2026-10-12 [#16 Show the AI draft before the production approval](https://github.com/a0966568571-bot/readme-activity-bot/pull/16), by a0966568571-bot
- 2026-10-12 [#15 Pin Copilot CLI; document the pipeline (+ prompt-injection test)](https://github.com/a0966568571-bot/readme-activity-bot/pull/15), by a0966568571-bot
- 2026-10-12 [#14 Release-notes agent on GitHub Copilot CLI](https://github.com/a0966568571-bot/readme-activity-bot/pull/14), by a0966568571-bot
- 2026-10-12 [#13 Agent: report non-JSON responses](https://github.com/a0966568571-bot/readme-activity-bot/pull/13), by a0966568571-bot
- 2026-10-12 [#12 Release-notes agent on GitHub Models](https://github.com/a0966568571-bot/readme-activity-bot/pull/12), by a0966568571-bot

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

## Deployment pipeline

Every push to `main` runs [deploy.yml](.github/workflows/deploy.yml):

1. `lint` (ruff) and `test` (Python 3.9 and 3.13) must pass before `build`.
2. `build` picks the next version from `VERSION` and the existing tags, then packs `build.zip`.
3. `deploy-dev` and `deploy-staging` publish that same zip as `dev-vX.Y.Z` and `staging-vX.Y.Z` prereleases. Each stage downloads what it published, checks the sha256, and deletes the release if the check fails.
4. `release-notes-agent` drafts release notes with GitHub Copilot CLI (read-only git tools, `ai-review` environment).
5. `deploy-production` waits for a required reviewer, who reads the draft first, then publishes `prod-vX.Y.Z`.
6. `notify` comments the result on the Release log issue (#7).

## Project tracking

Work is tracked on the [README Automation board](https://github.com/users/a0966568571-bot/projects/2).

- #1 Automate the Recent Activity section
- #2 CI guardrails and run reporting
- #7 Release log (deployment pipeline)
