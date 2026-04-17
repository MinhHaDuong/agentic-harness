---
name: start-ticket
description: Begin work on a ticket. Creates worktree, writes first test, transitions to Execute phase.
disable-model-invocation: true
user-invocable: true
argument-hint: <ticket-id>
---

# Start ticket — begin work on $ARGUMENTS

`[Plan → Execute]`

## Steps

1. Read the ticket (from git-erg `tickets/` directory or forge).
2. Check the **Exit criteria** section. If unclear, ask the author before writing code.
3. If not already in a worktree, enter one: call `EnterWorktree` with name `t$ARGUMENTS`.
4. Create or checkout the ticket branch:
   ```bash
   git switch -c t$ARGUMENTS-short-description
   ```
5. Read the files listed in **Relevant files**.
6. Write the first test from the **Test** section of the ticket.
7. Run `make check-fast` — confirm the test fails.
8. Announce `[Plan → Execute]`, then implement until `make check` passes.
9. Pre-PR self-gate: run `/verify-adherence <branch>` (the branch created in step 4).
   - Clean → proceed to step 10 and pass `--label verify:adherence-passed` to `gh pr create`. The label signals to the downstream `/verify` merge gate that the mechanical adherence phase already ran clean and can be skipped on its next pass.
   - Blockers → decide per blocker:
     - Cheap and mechanical (obvious fix, no design judgement) → fix in place, re-run `make check` and `/verify-adherence`, then proceed only once clean. Up to 2 fix-and-recheck cycles; if still not clean after 2 rounds, escalate.
     - Otherwise → STOP. Do not open the PR. Escalate with the adherence report and the blocker list.
   - Circuit breaker: if `/verify-adherence` itself errors, times out, or returns an unparseable result → ESCALATE. Do not open the PR and do not silently skip the gate.
10. Push the branch and open a merge request with `gh pr create ... --label verify:adherence-passed`.
11. Review according to `/review-pr`.
12. Fix all comments regardless of severity.
13. Repeat 11–12 up to 3 times. If still not clean, escalate (see workflow rules).
