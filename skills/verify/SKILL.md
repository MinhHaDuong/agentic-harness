---
name: verify
description: Run the full per-PR verification loop (adherence + review + review-pr + simplify), then gate through /verify-gate. Bounces the PR for at most one retry. Never merges.
disable-model-invocation: false
user-invocable: true
argument-hint: <pr-number>
context: fork
---

# Verify PR $ARGUMENTS — six-phase loop with anti-rubber-stamp gate

One skill, one PR, one decision: APPROVED / REROLL / ESCALATE. **Never merges.**
Merge is always the human's or the orchestrator's call.

## When to use

- Orchestrator Phase 6 (per-ticket verification before merge).
- Any time an author wants a full-depth check on a single PR before asking for merge.
- **Do NOT** use for quick sanity — use `/review` or `/review-pr` directly.

## Invariants

- Runs on exactly one PR.
- Two gate rounds maximum. Third round is forbidden — escalate instead.
- Never calls `gh pr merge`. The verdict is structured output; the caller decides.
- The fix loop between rounds makes commits on the PR branch; no changes to other branches.
- `--force-approve` is supported for explicit human override; it is logged loudly in the
  PR comments and the skill transcript.

## Phases

### 1. Setup

- `gh pr checkout $ARGUMENTS` into an isolated worktree. Abort if the PR is not mergeable
  or if there are open merge conflicts.
- Collect:
  - The ticket file referenced in the PR title or body (`tickets/*.erg`).
  - PR body, full diff, all existing review comments, all inline comments, all commit
    messages on the branch.
- If any of these cannot be located, ESCALATE with a clear message. Do not proceed.

### 2–4. Read-only review fan-out (parallel)

Launch in a single message, as background agents:

- `/verify-adherence <branch>` — mechanical-first rule check.
- `/review` (built-in) — standard review.
- `/review-pr` or `/review-pr-prose` — file-type heuristic: if any `*.qmd` changed → prose; else code.

Wait for all three to complete. Collect their outputs.

### 5. Simplify (sequential)

After 2–4 land their comments, run `/simplify <pr-number>`. This phase may commit fixes
to the PR branch. Wait for its fixes (if any) to land before the gate reads state.

### 6. Gate (the non-rubber-stamp step)

Invoke `/verify-gate <pr-number>`. It returns a structured verdict:

```yaml
verdict: APPROVED | REROLL | ESCALATE
per_exit_criterion: [...]
unresolved_review_comments: [...]
unresolved_simplify_findings: [...]
unresolved_adherence_violations: [...]
rationale: <paragraph>
round: 1 | 2
```

## Branch on verdict

- **APPROVED** → post a "verify: approved" comment on the PR summarising the evidence. End
  the skill. The caller merges.
- **REROLL, round 1** → spawn a fix subagent with `isolation: "worktree"`, feeding it the
  unresolved lists as input. Fix agent gets ≤10 min. On push, re-enter phase 6 with
  `round=2`.
- **REROLL, round 2** → upgrade to ESCALATE (no third round). Post a PR comment with the
  still-unresolved items and the gate's rationale. End the skill.
- **ESCALATE** → post a PR comment tagged `/verify stopped:` listing what needs human
  judgment. End the skill.

## Fix-agent contract

The subagent spawned on REROLL receives:

- Worktree path (PR branch already checked out).
- Unresolved lists from the gate verdict (review comments, simplify findings, adherence
  violations, per-exit-criterion gaps).
- Strict rule: **only** the listed items. No scope creep. No "while I'm here" edits.
- TDD discipline still applies: add a failing test for any behavioural fix before coding.

Push commits to the PR branch; do not open new PRs. Trigger re-entry into phase 6.

## Circuit breakers

- Setup step cannot find ticket file → ESCALATE.
- Any of phases 2–5 errors or times out → ESCALATE (do not silently skip).
- Fix agent timeout (10 min) → ESCALATE.
- Gate disagrees with phase 2–5 on a must-fix finding → ESCALATE (no silent resolution).
- Two REROLL rounds reached → ESCALATE.
- Telemetry thresholds (see `## Telemetry`).

## Telemetry

A `/verify` run with no progress signal is indistinguishable from a runaway.
Every run emits runtime + cost so the reader can calibrate.

### Per-phase timing (stderr only)

Before and after each phase (1 setup, 2–4 review fan-out, 5 simplify, 6 gate,
fix-agent rounds), print one line to stderr:

```
[verify] phase=<name> start=<ISO-8601>
[verify] phase=<name> end=<ISO-8601> elapsed=<seconds>s
```

Stderr only — never posted to the PR. Intended for log capture, not review.

### Verdict footer (PR comment)

Append exactly one line to the verdict comment (APPROVED / REROLL / ESCALATE):

```
telemetry: wall=<seconds>s agents=<n> tokens=<in+out> cost≈$<usd>
```

- `wall` — seconds from phase-1 start to verdict post.
- `agents` — count of sub-agent invocations (review, review-pr, simplify,
  verify-adherence, fix agent, gate).
- `tokens` — sum of input + output across all sub-agents and the driver,
  as reported by the SDK/agent results.
- `cost≈` — best-effort USD estimate using current model rates; prefix with
  `≈` since it's an approximation, not a billed figure.

### Thresholds (configurable)

Thresholds are read from `skills/verify/telemetry.yml`. Each is overridable
per-run via the env var listed in that file. Defaults:

| Signal | Warn (continue) | Escalate (stop) |
|--------|-----------------|-----------------|
| Wall   | 15 min          | 30 min          |
| Tokens | 500k            | 1M              |

Behaviour on breach:

- **Warn** → post a short PR comment `verify: slow run` / `verify: token-heavy
  run` with the measured value, then continue the run. One warning per signal
  per run (no spam on re-entry for round 2).
- **Escalate** → stop the run, post a `/verify stopped:` comment explaining
  which threshold tripped and the measured value, skip remaining phases. Add
  the telemetry footer before exit so the human sees the numbers that caused
  the escalation.

Check thresholds at phase boundaries, not inside phases — a mid-phase abort
leaves the PR in an unclear state.

## `--force-approve`

Explicit human override. Usage: `/verify <pr-number> --force-approve <reason>`.

- Skips phase 6 gate.
- Posts a loud PR comment: `/verify: force-approved — reason: <reason>`. Includes the
  outputs of phases 2–5 so reviewers see what was waived.
- Logs the override in the skill transcript.
- Still does not merge.

## Not in scope

- **Wave-level integration review.** Verify one PR at a time. Use a separate
  `/verify-wave` (not yet drafted) for post-merge integration testing of a batch.
- **Merging.** Ever. That is the caller's job.

## Output shape

Post a single top-level PR comment at end of skill. Template:

```
/verify round=<n> verdict=<V>

Exit criteria:
- <criterion 1>: ADDRESSED — <evidence>
- <criterion 2>: MISSING — <gap>
...

Unresolved review comments: [list or "none"]
Unresolved simplify: [list or "none"]
Adherence: PASS | FAIL (<count>)

Rationale:
<paragraph>

telemetry: wall=<seconds>s agents=<n> tokens=<in+out> cost≈$<usd>
```
