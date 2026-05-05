<!-- last-reviewed: 2026-04-29 -->
# Git Discipline

- **Always work on a branch.** Main is read-only except for STATE housekeeping.
- **Run `git status` before every commit.** Staged leftovers from an interrupted previous session will be silently bundled into the next commit.
- **One change per commit.** Message explains *why this change and not another*: alternatives considered, local design choices made.
- **Merge commits**: strategic-level detail — architecture decisions, cross-file impacts, residual debt. Feature merges go through merge requests; chores merge locally via short-lived branch + fast-forward.
- **Git is the project's long-term memory.** Top-level files reflect *now* — history lives in `git log`.
- **Worktree isolation is automatic** — the SessionStart hook enforces it. All worktrees are throwaway; branches hold durable state.
- **Create a merge request** for each ticket to review changes before merging.
- **Delete branches after merge.** All repos use `deleteBranchOnMerge: true` on GitHub, so the remote branch disappears automatically when a PR merges. Clean up stale local branches with:
  ```bash
  git fetch --prune
  git branch -vv | awk '/: gone]/{print $1}' | xargs -r git branch -D
  ```
  The healthcheck's branch hygiene check flags stale locals; this is how to resolve them. Do not use `git branch -D` on a branch whose PR you have not verified is merged.
- **Don't gitignore handoff artifacts.** Generated files that a downstream workpackage consumes (figures, tables, macros `\input`ed by the manuscript) are durable state — commit them. Caches, LaTeX aux files, and the final rendered PDF are regenerable — gitignore.
