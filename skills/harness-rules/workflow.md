<!-- last-reviewed: 2026-04-04 -->
# Session Start

At the beginning of every conversation:

> Setup (env, git identity, hooks path, GH_TOKEN) and project STATE are delivered by the SessionStart hook.

## 1. Isolate and announce phase

**GATE — nothing below this step runs until the worktree is entered.**

Every conversation runs in its own worktree. Call `EnterWorktree` with a descriptive name, then checkout the right branch and announce the phase. This ensures parallel conversations never interfere with each other.

| Context | Worktree name | Then | Phase |
|---------|---------------|------|-------|
| Fresh conversation, no ticket | `explore-{topic}` | Create branch `explore-{topic}` | `[→ Imagine]` |
| Ticket reference but no branch | `explore-{topic}` | Create branch `explore-{topic}` | `[→ Plan]` |
| `/start-ticket N` | `t{N}` | Create or checkout branch `t{N}-short-description` | `[→ Execute]` |
| Active feature branch + open PR | `t{N}` | Checkout existing branch | `[→ Execute]` |
| PR review | `review-{N}` | Checkout PR branch | `[→ Verify]` |

After `EnterWorktree`, run `git switch <branch>` (or `git switch -c <branch>`) to land on the correct branch. The worktree is throwaway — all durable state lives in branches.

# Escalation Protocol

When stuck, escalate progressively:
1. Fix direct — review feedback is straightforward.
2. Alternative approach — rethink the solution.
3. Parallel expert agents — fan-out different directions.
4. Re-ticket with diagnosis — the problem is mis-specified.
5. Stop — ask the author.

Save a feedback memory at each escalation (what failed, why). Stop if repeating yourself.

# When to Ask the Author

- You're stuck after three different approaches (including expert fan-out).
- The task requires a judgment call outside your domain docs.

# Compaction

When compacting, preserve the list of modified files, test commands, and current implementation plan.
