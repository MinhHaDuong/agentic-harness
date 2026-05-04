---
name: raid
description: Run an Imperial Dragon raid across multiple tickets. Picks targets, manages waves, enforces isolation. Always autonomous — never merges.
disable-model-invocation: false
user-invocable: true
argument-hint: [ticket-ids or "all open"]
model: claude-opus-4-6
effort: max
---

# Raid $ARGUMENTS — Imperial Dragon hunt

A raid does not redefine skills. It calls `/start-ticket`,
`/review-pr`, `/celebrate`, etc. Its job is sequencing, wave management,
and enforcing invariants. It never merges — all work lands as merge requests
for the author to review.

## Balance rule

**Deliverable work ≥60%, tooling ≤40%.** If two consecutive tickets were tooling, the next must advance a deliverable. Track in session log.

**Deliverables**: items in `STATE.md` under current milestone — papers, slides, reading notes, figures, responses to reviewers. Tooling: tests, hygiene, refactoring, harness improvements.

**Escape hatch**: if `make check-fast` fails and blocks all deliverable work, tooling may exceed 40%. Document why.

## Checkpointing

Every phase ends with a git commit. If the session dies, resume by
reading the ticket logs and git history to determine which phase
completed last. The checkpoint is the repo, not session state.

## Phase 1: Select

If $ARGUMENTS is "all open": read open tickets from git-erg `tickets/` or forge.
Otherwise: parse comma-separated ticket IDs.

Prioritize:
1. Scientific deliverables first
2. Gaps with north star (STATE.md)
3. Ripest open issues
4. Inline markers (FIXME, TODO, HACK)

Read each ticket + STATE.md. Group by milestone. Identify dependency order and wave structure.

## Phase 2: Imagine (parallel)

For each ticket, launch an agent (background, no isolation needed — read-only):
- Read ticket + STATE.md + surrounding code
- Reimagine: why now, why this scope, what's the simplest path
- **Antipattern scan (scope).** YAGNI (search the package registry —
  don't hand-roll what a library already does), premature abstraction.
  Annotate any hits with the proposed fix.

Wait for all. Commit reimagined tickets. Report scorecard.

## Phase 3: Plan (parallel)

For each reimagined ticket, launch an agent (background):
- Read ticket + actual source code
- Write Actions, first test, dependencies
- **Antipattern scan.** Tautological tests — would this test catch a
  wrong implementation, or only a different one? Annotate any hits
  with the proposed fix.

Wait for all. Commit planned tickets. Report scorecard.

## Phase 4: Verify feasibility

Launch agents by cluster to cross-check plans:
- File paths, line numbers, function signatures
- Data assumptions, API key requirements
- Cross-ticket conflicts

Annotate tickets with PASS/WARN/BLOCK. Commit annotations.

## Phase 5: Execute (waves, worktree-isolated)

Group tickets into waves:
- Wave N: no unmerged dependencies
- Wave N+1: depends on Wave N results

For each wave, launch agents with `isolation: "worktree"`.
Each agent follows `/start-ticket` workflow. Push branch when done, create merge request.

Wait for wave to complete.

## Phase 6: Verify (per-ticket `/verify`)

Mood: Be strict, skeptical, nit-picky, detail-oriented. Aim for code excellence and integrity.

**Per-ticket:** invoke `/verify <pr-number>` on each merge request. The skill runs:

1. `/verify-adherence` — mechanical-first rule check (tests + grep ratchet before LLM).
2. `/review` (built-in) — standard review.
3. `/review-pr` or `/review-pr-prose` — file-type heuristic.
4. `/simplify` — reuse/quality/efficiency, applies fixes.
5. `/verify-gate` — anti-rubber-stamp merge gate: APPROVED / REROLL / ESCALATE.
6. On REROLL (round 1 only), `/verify` spawns a fix agent and re-gates; round 2 escalates.

`/verify` never merges. The raid does not either — merges are always the
author's call (interactive) or the `/celebrate` flow's call (autonomous).

**Per-wave:** after all per-ticket `/verify` runs complete, launch one integration-review
subagent (read-only) to check:
- Do the merged/merge-pending PRs compose without contradiction?
- Does `make check` still pass if we imagine them all merged?
- Are there testing gaps visible only at wave granularity (e.g., two PRs touching the
  same test file in incompatible ways)?

Wave-level findings go to the human as a wave-summary comment; they do not block
individual `/verify` verdicts.

## Phase 7: Scope audit

Check each merge request for scope creep — did Execute exceed the Plan?

**Token economy rule**: Any time a ticket must be created in any phase, invoke
`/ticket-new` — never write the file directly or compute the next ID manually.
`/ticket-new` calls `erg next-id` and `erg validate`, keeping mechanical work
inside the tool where it belongs.

For each out-of-scope finding, choose one outcome:

- **CLEAN** — no scope creep found; continue.
- **TICKETED** — create a new ticket via `/ticket-new` for the out-of-scope work.
  Leave commits in the PR. Add a line to the PR body: `Scope overflow: #NNNN`.
  Do not rewrite git history.
- **ESCALATE** — scope creep is present but cannot be cleanly ticketed (ambiguous
  ownership, no clear ticket boundary, or you are uncertain). Stop. Leave a
  comment on the merge request explaining what was found. Human decides.

**Never** rebase or amend commits to excise scope creep.

## Mid-session checkpoint (~50% effort)

- [ ] Opened at least one deliverable-forward merge request?
- [ ] Tooling/deliverable ratio within bounds?
- [ ] Self-reviewed at least one merge request?
- [ ] `make check` passes on main?

Autonomous mode: ralph loop to next wave.

## Wrap up

1. `make check` on main — compare against baseline. New failures → ticket.
1b. Scan all tickets for bump lines and print a tally:
    ```
    grep -h ' bump ' tickets/*.erg | awk '{print $4}' | sort | uniq -c | sort -rn
    ```
    Format as: `Ticket NNNN: N bumps (X permission, Y verify-reroll, …) → Z% trivial`
2a. Interactive mode: All work pushed, merge requests open.
2b. Autonomous mode: All merge requests merged, main green.
3. Write briefing (session log + merge request list + test delta).
4. Do NOT run `/end-session`.

## Circuit breakers

All three triggers below require a bump log line written to the **main-repo**
`tickets/` directory (not the killed agent's worktree copy), committed before
relaunching: `{ISO8601} claude bump circuit-breaker — {reason}`.

**Agent timeout**: If an agent has not pushed within 10 minutes,
kill it. Split the ticket or relaunch with narrower scope.
Bump reason: `agent timeout`.

**Ping-pong detector**: If two agents edit the same file on the
same branch, STOP. Reset to last known-good commit, relaunch ONE agent.
Bump reason: `ping-pong on {file}`.

**Redirect ban**: Do not use SendMessage to redirect a running
agent. Kill and relaunch with corrected instructions.
Bump reason: `redirect ban triggered`.

**Escalation**: If the same fix fails twice, stop and leave a
ticket comment with the two failed approaches.
