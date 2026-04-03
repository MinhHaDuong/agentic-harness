---
name: celebrate
description: Post-task wrap-up. Reflects on completed work, updates project state, cleans up branches.
disable-model-invocation: false
user-invocable: true
---

# Celebrate — post-task wrap-up

`[Execute → Celebrate]`

Do not skip steps.

## Reflect and update

1. **Reflect**: what worked, what didn't, what was surprising.
2. **Sweep for similar patterns**: review the fix just completed. Grep/audit the codebase for the same anti-pattern in other files. File tickets for all instances found.
3. **Update STATE.md**: rewrite per spec in rules. Check off completed milestones. Delete items checked off before this session. No changelog.
4. **Update project docs** if pipeline, data contract, or methodology changed.
5. **Save persistent memory**: durable lessons from this task. No sweep here — sweeps happen at `/end-session`.
6. **Commit** the updates on the current branch (before merging).

## Close and clean up

7. **Merge to main**: feature work through PR. Chores merge locally via short-lived branch + fast-forward.
8. **Push** and **clean up**: delete remote branch after merge.
9. **Close** the ticket if still open.
10. **Check for tracking ticket**: if the closed ticket has a parent, check whether all sibling sub-tickets are now closed.
    - All closed → integration review: re-read all child PR diffs, run full test suite, verify exit criteria.
    - Any open → do nothing, tracker stays open.
11. **Exit worktree**: call `ExitWorktree` with action `remove` — the worktree is throwaway, all state is in the branch/PR.
12. **Verify hygiene**:
    - `git branch -a` → no stale remote branches
    - `gh pr list` → no stale PRs
13. **Offer** to improve workflow rules if lessons were learned.
