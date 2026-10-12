# readme-activity-bot

[![Update README](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/update-readme.yml/badge.svg?branch=main)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/update-readme.yml)
[![Validate README](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/validate-readme.yml/badge.svg?branch=main)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/validate-readme.yml)

This README keeps its own **Recent Activity** section up to date.
A GitHub Actions workflow reads the latest commits, merged pull requests and closed issues from the GitHub REST API, then rewrites only the block between the two markers below.

## Recent Activity

<!-- ACTIVITY:START -->
_Updated automatically by GitHub Actions. Do not edit this block by hand._

**Latest commits**

- 2026-10-12 [`79d6eb8`](https://github.com/a0966568571-bot/readme-activity-bot/commit/79d6eb83b653f5c1f40e08c46cf4c61f367ef3e8) Merge pull request #14 from a0966568571-bot/copilot-agent, by a0966568571-bot
- 2026-10-12 [`5f24d82`](https://github.com/a0966568571-bot/readme-activity-bot/commit/5f24d821c4471db7493a43e1090ca81872278395) Run the release-notes agent with GitHub Copilot CLI, by a0966568571-bot
- 2026-10-12 [`7ae70d2`](https://github.com/a0966568571-bot/readme-activity-bot/commit/7ae70d2b578f260d44fa30e68ef0788358085779) Merge pull request #13 from a0966568571-bot/agent-debug, by a0966568571-bot
- 2026-10-12 [`255ae82`](https://github.com/a0966568571-bot/readme-activity-bot/commit/255ae826c5c49f85a671005537b55288d28c8772) Say what the Models API actually returned when it is not JSON, by a0966568571-bot
- 2026-10-12 [`08c4d3f`](https://github.com/a0966568571-bot/readme-activity-bot/commit/08c4d3fe4bb0ffc4a3c913b52bc3d53d6a35f945) Merge pull request #12 from a0966568571-bot/github-models-agent, by a0966568571-bot

**Recently merged pull requests**

- 2026-10-12 [#14 Release-notes agent on GitHub Copilot CLI](https://github.com/a0966568571-bot/readme-activity-bot/pull/14), by a0966568571-bot
- 2026-10-12 [#13 Agent: report non-JSON responses](https://github.com/a0966568571-bot/readme-activity-bot/pull/13), by a0966568571-bot
- 2026-10-12 [#12 Release-notes agent on GitHub Models](https://github.com/a0966568571-bot/readme-activity-bot/pull/12), by a0966568571-bot
- 2026-10-12 [#11 Show the agent's result line in the log](https://github.com/a0966568571-bot/readme-activity-bot/pull/11), by a0966568571-bot
- 2026-10-12 [#10 Fix release-notes agent: use maintained base-action](https://github.com/a0966568571-bot/readme-activity-bot/pull/10), by a0966568571-bot

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
