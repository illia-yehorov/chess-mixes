# AI contributor rules

These instructions apply to AI agents working in this repository. Read this file **before** changing code, opening a branch, or creating a Pull Request.

## Git history and Pull Requests

- **Never commit directly to `main`.** Work in a dedicated feature branch and open a Pull Request for review.
- **Never merge a Pull Request** unless the user explicitly requests it.
- **One user-requested change = one logical commit.** Prepare *all related file changes* together (implementation, tests, documentation, config, workflows) and commit them **once**, not file by file.
- Before committing, inspect the relevant existing files, finish the complete change, and run the available relevant tests when practical. Fix any issues **before** the commit.
- For GitHub API tools, batch file changes into a **single tree and commit** (or stage all files and run one `git commit` in a local checkout). Avoid per-file GitHub write calls, which each create a separate commit.
- For further user-requested work on an already published PR, add **at most one new commit per requested iteration**, grouping all related changes. A follow-up request is a new iteration; do not silently rewrite previous commits.
- **Do not rewrite published Git history:** no `git commit --amend`, rebase of published branches, `git reset` to replace published commits, force push, or force-with-lease.
- If the user wants **one commit in `main`** from a multi-commit PR, recommend GitHub's **Squash and merge** during review. It produces one commit in `main` without changing the published feature branch's history. Do not perform the merge without an explicit request.
- Use English for branch names, commit messages, and Pull Request titles/descriptions. Prefer descriptive, task-scoped names.

## Chess Mixes project

- Preserve existing Python generator behavior, TOML configuration support, HTML/JavaScript puzzle selection, localStorage history, and the familiar `chess-generate.bat 1|2|3` interface.
- Keep the large `chess/lichess_db_puzzle.csv.zst` database outside Git.
- Treat `site/mixes/` as the location for newly generated publishable HTML files. Never reintroduce historical generated HTML as part of migration or maintenance.
- Keep GitHub Pages publishing separate from future puzzle-integrity verification. Do not auto-regenerate mixes only because Lichess updated its database.
- Prefer simple static-site solutions and avoid new infrastructure without a clear need.
