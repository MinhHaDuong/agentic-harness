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
2. **Log to telemetry**: pipe a JSON summary to `~/.claude/skills/celebrate/log-celebration`:
   ```bash
   echo '{"project":"<name>","branch":"<branch>","commits":<n>,"files_changed":<n>,"ticket":<number|null>}' | ~/.claude/skills/celebrate/log-celebration
   ```
3. **Sweep for similar patterns**: review the fix just completed. Grep/audit the codebase for the same anti-pattern in other files. File tickets for all instances found.
4. **Update STATE.md**: rewrite per spec in rules. Check off completed milestones. Delete items checked off before this session. No changelog. **Concurrency**: STATE.md may be modified by other worktrees. Before writing, re-read the file to get the latest version. After committing, if push fails due to conflict, pull --rebase, re-read STATE.md, reapply your changes, and commit again.
5. **Update project docs** if pipeline, data contract, or methodology changed.
6. **Save persistent memory**: durable lessons from this task. No sweep here — sweeps happen at `/end-session`.
7. **Branch guard then commit**: run `git branch --show-current` and verify you are on the expected branch before committing. If wrong, switch first — never commit blindly.

## Close and clean up

8. **Merge to main**:
   - Detect worktree: `git rev-parse --git-common-dir` vs `git rev-parse --git-dir`. If they differ, you are in a worktree.
   - **In a worktree**: do NOT run `git switch main` — it will fail. Instead push the branch and merge via PR (`gh pr create` then `gh pr merge --ff-only`), or for chore-level work push directly: `git push origin HEAD:main`.
   - **Not in a worktree**: feature work through PR. Chores merge locally via short-lived branch + fast-forward.
9. **Push** and **clean up**: delete remote branch after merge.
10. **Close** the ticket if still open.
11. **Check for tracking ticket**: if the closed ticket has a parent, check whether all sibling sub-tickets are now closed.
    - All closed → integration review: re-read all child PR diffs, run full test suite, verify exit criteria.
    - Any open → do nothing, tracker stays open.
12. **Exit worktree** (if in one): call `ExitWorktree` with action `remove`. Skip if not in a worktree.
13. **Verify hygiene**:
    - `git branch -a` → no stale remote branches
    - `gh pr list` → no stale PRs
14. **Offer** to improve workflow rules if lessons were learned.
