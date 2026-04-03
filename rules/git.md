<!-- last-reviewed: 2026-04-04 -->
# Git Discipline

- **Always work on a branch.** Main is read-only except for STATE housekeeping.
- **One change per commit.** Message explains *why this change and not another*: alternatives considered, local design choices made.
- **Merge commits**: strategic-level detail — architecture decisions, cross-file impacts, residual debt. Feature merges go through PRs; chores merge locally via short-lived branch + fast-forward.
- **Git is the project's long-term memory.** Top-level files reflect *now* — history lives in `git log`.
- **Every conversation runs in a worktree** — `EnterWorktree` at session start, `ExitWorktree` at end. All worktrees are throwaway; branches hold durable state.
- **Create PR** for each ticket to review changes before merging.
