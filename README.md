# readme-activity-bot

This README keeps its own **Recent Activity** section up to date.
A GitHub Actions workflow reads the latest commits, merged pull requests and closed issues from the GitHub REST API, then rewrites only the block between the two markers below.

## Recent Activity

<!-- ACTIVITY:START -->
_Updated automatically by GitHub Actions. Do not edit this block by hand._

**Latest commits**

- 2026-10-05 [`3cd2bd8`](https://github.com/a0966568571-bot/readme-activity-bot/commit/3cd2bd8310e14b8282890bdbd2d2a5865848b0ad) Merge pull request #3 from a0966568571-bot/1-update-readme-activity, by a0966568571-bot
- 2026-10-05 [`ee79209`](https://github.com/a0966568571-bot/readme-activity-bot/commit/ee792094903073177f6d084f549e144143375ad6) Add README update script, tests and workflow, by a0966568571-bot
- 2026-10-05 [`92da88b`](https://github.com/a0966568571-bot/readme-activity-bot/commit/92da88b1b01ad82551535450812b5cca975616b1) Add README template with activity markers, by a0966568571-bot
- 2026-10-05 [`9cbc742`](https://github.com/a0966568571-bot/readme-activity-bot/commit/9cbc74286c955962c14505d2078096fda9fab649) Initial commit, by a0966568571-bot

**Recently merged pull requests**

- 2026-10-05 [#3 Automate README Recent Activity section](https://github.com/a0966568571-bot/readme-activity-bot/pull/3), by a0966568571-bot

**Recently closed issues**

- 2026-10-05 [#1 Automate README "Recent Activity" section with GitHub Actions](https://github.com/a0966568571-bot/readme-activity-bot/issues/1)
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
