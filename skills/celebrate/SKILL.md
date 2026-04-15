---
name: celebrate
description: Post-task wrap-up. Reflects on completed work, updates project state, cleans up branches.
disable-model-invocation: false
user-invocable: true
---

# Celebrate — post-task wrap-up

`[Execute → Celebrate]`

Run after the branch has been merged. Do not skip steps.

## Pre-check

Verify the branch has been merged before proceeding:
```bash
git branch --merged main | grep -q "$(git branch --show-current)"
```
If the current branch is not merged into main, stop and tell the user. Do not continue with celebrate.

## Reflect and update

1. **Reflect**: what worked, what didn't, what was surprising.
2. **Log to telemetry**: pipe a JSON summary to `~/.claude/skills/celebrate/log-celebration`:
   ```bash
   echo '{"project":"<name>","branch":"<branch>","commits":<n>,"files_changed":<n>,"ticket":<number|null>}' | ~/.claude/skills/celebrate/log-celebration
   ```
3. **Sweep for similar patterns**: review the fix just completed. Grep/audit the codebase for the same anti-pattern in other files. File tickets for all instances found.
4. **Update project docs** if pipeline, data contract, or methodology changed.
5. **Save persistent memory**: durable lessons from this task. No sweep here — sweeps happen at `/end-session`.

## Close and clean up

6. **Close** the ticket if still open.
7. **Check for tracking ticket**: if the closed ticket has a parent, check whether all sibling sub-tickets are now closed.
    - All closed → integration review: re-read all child diffs, run full test suite, verify exit criteria.
    - Any open → do nothing, tracker stays open.
8. **Exit worktree** (if in one): call `ExitWorktree` with action `remove`. Skip if not in a worktree.
9. **Verify hygiene**:
    - `git branch -a` → no stale remote branches
    - Check for stale merge requests
10. **Offer** to improve workflow rules if lessons were learned.

Note: STATE.md is updated on main during `/end-session`, not here.
