---
name: end-session
description: End-of-day session wrap-up. Pushes branches, runs tests, refreshes STATE, offers autonomous session.
disable-model-invocation: false
user-invocable: true
---

# End session — day wrap-up

Run when the user ends a work session ("done for today", "let's stop", "wrap up").

## Steps

1. **Reflect on the session** — summarize work done. `git log --since="6am" --oneline` as starting point.
2. **Log session metrics** — run `~/.claude/skills/end-session/log-agent-metrics` with: `<session_id> session <total_tokens> <tool_uses> <duration_ms> <model> <project>`. Estimate tokens from conversation length if exact count unavailable.
3. **Push all branches** — no local-only work overnight. `git branch` → ensure each non-main branch is pushed.
4. **Commit WIP if needed** — uncommitted work gets `wip:` prefix and push.
5. **Handoff notes** — for in-progress tickets with unpushed context, add a comment to the ticket: what's done, what's next, blockers.
6. **Hygiene sweep**:
   - `git worktree list` → remove any stale worktrees (`git worktree prune`)
   - `git branch -a` → delete stale remote branches
   - Check for orphan tickets and stale merge requests
7. **Full test suite** — `make check` on main. New failures → open ticket (tag `bug`). Known failures → confirm still open.
8. **Refresh STATE.md** on a throwaway branch per rules:
   a. `git checkout -b housekeeping-state-YYYY-MM-DD main`
   b. Rewrite STATE: current stats, blockers, next actions, milestones. No changelog.
   c. Prune: delete items checked off before this session.
   d. Commit, merge to main via fast-forward, delete branch.
9. **Memory sweep** — follow `/memory` skill (includes staleness check + rule cross-reference).
10. **Autonomous session** — offer to launch `/autonomous` if user wants unsupervised work.
