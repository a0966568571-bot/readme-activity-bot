# readme-activity-bot

[![Update README](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/update-readme.yml/badge.svg?branch=main)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/update-readme.yml)
[![Validate README](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/validate-readme.yml/badge.svg?branch=main)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/validate-readme.yml)
[![Deploy](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/deploy.yml/badge.svg?branch=main)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/deploy.yml)
[![tests](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fa0966568571-bot%2Freadme-activity-bot%2Fbadges%2Ftests.json)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/deploy.yml)
[![coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fa0966568571-bot%2Freadme-activity-bot%2Fbadges%2Fcoverage.json)](https://github.com/a0966568571-bot/readme-activity-bot/actions/workflows/deploy.yml)

This README keeps its own **Recent Activity** section up to date.
A GitHub Actions workflow reads the latest commits, merged pull requests and closed issues from the GitHub REST API, then rewrites only the block between the two markers below.

## Recent Activity

<!-- ACTIVITY:START -->
_Updated automatically by GitHub Actions. Do not edit this block by hand._

**Latest commits**

- 2026-10-20 [`a07113a`](https://github.com/a0966568571-bot/readme-activity-bot/commit/a07113a9cba1d2e1eecfd02c915430d2f666b006) Merge pull request #19 from a0966568571-bot/e-test-stages, by a0966568571-bot
- 2026-10-20 [`6d5cddb`](https://github.com/a0966568571-bot/readme-activity-bot/commit/6d5cddb5618d53ad6342957da696e1da84cda7c9) Split the test gate into unit, integration and prod stages, by a0966568571-bot
- 2026-10-20 [`21ac27a`](https://github.com/a0966568571-bot/readme-activity-bot/commit/21ac27a7576aa968ccf44982357f0e8991a2850e) Merge pull request #18 from a0966568571-bot/test-gates, by a0966568571-bot
- 2026-10-20 [`0e00ce0`](https://github.com/a0966568571-bot/readme-activity-bot/commit/0e00ce05ee62f16d069c7e17645400b0ad3b8627) Add a test gate between build and release, by a0966568571-bot
- 2026-10-12 [`b4bbf64`](https://github.com/a0966568571-bot/readme-activity-bot/commit/b4bbf64b23066d4b1287ebf12772f5d7ba8398d6) Merge pull request #17: post AI draft only when production waits \[skip ci\], by a0966568571-bot

**Recently merged pull requests**

- 2026-10-20 [#19 Separate test stages with TEST_ENV gates before staging and production](https://github.com/a0966568571-bot/readme-activity-bot/pull/19), by a0966568571-bot
- 2026-10-20 [#18 Test gate between build and release](https://github.com/a0966568571-bot/readme-activity-bot/pull/18), by a0966568571-bot
- 2026-10-12 [#17 Post the AI draft only when production will ask for review](https://github.com/a0966568571-bot/readme-activity-bot/pull/17), by a0966568571-bot
- 2026-10-12 [#16 Show the AI draft before the production approval](https://github.com/a0966568571-bot/readme-activity-bot/pull/16), by a0966568571-bot
- 2026-10-12 [#15 Pin Copilot CLI; document the pipeline (+ prompt-injection test)](https://github.com/a0966568571-bot/readme-activity-bot/pull/15), by a0966568571-bot

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

1. `lint` (ruff) runs first, then `build` picks the next version from `VERSION` and the existing tags and packs `build.zip`.
2. Test stage 1, `test-unit`: unit tests on Python 3.9 and 3.13 (Linux) and 3.13 (macOS), with JUnit XML and a coverage report for each. `coverage-gate` skips every release when coverage is below the `COVERAGE_MIN` variable (90%).
3. Test stage 2, `test-integration` (`TEST_ENV=staging`): downloads `build.zip` and runs the tests in [tests/integration](tests/integration), which unzip the artifact and run the shipped code against a fake GitHub API. If either stage fails, every release job is skipped.
4. `deploy-dev` and `deploy-staging` publish that same zip as `dev-vX.Y.Z` and `staging-vX.Y.Z` prereleases. Each stage downloads what it published, checks the sha256, and deletes the release if the check fails. Staging deploys only from `main`.
5. Test stage 3, `test-prod` (`TEST_ENV=prod`): the integration tests again, plus a check that the zip is byte for byte the one on the staging release. Both integration runs use [integration-tests.yml](.github/workflows/integration-tests.yml).
6. `release-notes-agent` drafts release notes with GitHub Copilot CLI (read-only git tools, `ai-review` environment).
7. `deploy-production` runs only after `test-prod` passes, waits for a required reviewer, who reads the draft first, then publishes `prod-vX.Y.Z`.
8. `notify` comments the test and release results on the Release log issue (#7).
9. `test-report` merges every JUnit file into one table in the run summary, updates the tests and coverage badges, and opens a `Tests failing on <branch>` issue when tests fail. The first run where they pass again closes it.

On branches other than `main` the pipeline runs the tests and stops: nothing is released.

## Project tracking

Work is tracked on the [README Automation board](https://github.com/users/a0966568571-bot/projects/2).

- #1 Automate the Recent Activity section
- #2 CI guardrails and run reporting
- #7 Release log (deployment pipeline)
