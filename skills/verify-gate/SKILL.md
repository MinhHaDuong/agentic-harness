---
name: verify-gate
description: Anti-rubber-stamp merge gate. Validates every ticket exit criterion and every review comment against the actual diff. Emits APPROVED / REROLL / ESCALATE with explicit evidence. Never merges.
disable-model-invocation: false
user-invocable: true
argument-hint: <pr-number>
context: fork
---

# Verify gate — PR $ARGUMENTS

The last line of defence before merge. A gate with teeth: **cannot approve without
concrete per-criterion evidence**. Designed to be called by `/verify` at phase 6, but
standalone-callable for debugging.

## Non-negotiables

1. **No rubber-stamp.** "CI ran" / "the simplify pass ran" / "all tests pass" are NOT
   evidence. Evidence must cite the *change* (commit SHA + file:line) or the *test*
   (test_id) that closes the gap.
2. **Exit criteria are contract.** Every item in the ticket's "Exit criteria" section must
   get an explicit ADDRESSED/MISSING verdict with evidence. A missing criterion cannot be
   papered over.
3. **Review comments are load-bearing.** Every review comment (from `/review`,
   `/review-pr`, human authors) is either ADDRESSED (commit changed the cited file, OR
   the comment was marked resolved, OR a ticket was opened with the rationale) or
   UNRESOLVED. No "I'll get to it later."
4. **Simplify findings are load-bearing.** Every must-fix from `/simplify` is either
   applied (diff shows the change) or explicitly justified in a PR comment that the gate
   agent validates.
5. **Adherence violations are blocking.** Any `blocking` entry from `/verify-adherence`
   is a REROLL trigger.
6. **Two rounds max.** Round 1 is initial gate. Round 2 is post-fix re-gate. Round 3 is
   forbidden — escalate.

## Input

Either:
- `<pr-number>` (standalone mode): the gate resolves ticket, diff, comments itself.
- A structured bundle from `/verify` (preferred): `{pr, ticket, diff, phase_outputs, round}`.

Both paths produce the same verdict shape.

## Evidence discovery

For each ticket exit criterion, the gate searches:

- **Commit messages** on the PR branch for the criterion's key phrases.
- **Diff** for files the criterion mentions (scripts, tests, docs).
- **Test suite** for test IDs that match the criterion's verification claim.
- **PR body** for explicit statements with references.

A criterion cannot be ADDRESSED solely on "the PR says so." Either a commit touched the
relevant file, or a test exists that covers the behaviour, or a rationale is posted.

For each review comment, the gate searches:

- **Commits made AFTER the comment timestamp** for changes to the commented file/line.
- **Comment resolution status** (GitHub's `resolved`/`outdated` flag).
- **Reply threads** for author acknowledgment + follow-up ticket reference.

A comment is UNRESOLVED if none of the above applies.

## Verdict shape

```yaml
verdict: APPROVED | REROLL | ESCALATE
round: 1 | 2
pr: <pr-number>
ticket: <ticket-id>

per_exit_criterion:
  - criterion: "<verbatim text from ticket>"
    status: ADDRESSED | MISSING
    evidence: "<commit SHA + file:line | test_id | PR body statement>"

unresolved_review_comments:
  - comment_ref: <url or id>
    author: <login>
    thread_excerpt: "<short>"
    why_unresolved: "<reason>"

unresolved_simplify_findings:
  - finding: "<verbatim>"
    severity: must-fix | nice-to-have
    status: NOT_APPLIED | APPLIED_PARTIAL | WAIVED_WITHOUT_RATIONALE

unresolved_adherence_violations:
  - rule_ref: "<.claude/rules/foo.md#bar>"
    file: <path>
    line: <n>
    severity: blocking | nit

rationale: |
  <one paragraph: what is the strongest remaining reviewer attack on this PR?
   if APPROVED, state why the evidence holds up to adversarial reading.>

second_round_needed:
  # populated only if verdict == REROLL
  - <each item from the unresolved lists, prioritised>
```

## Decision rules

- Any `MISSING` in `per_exit_criterion` → REROLL (round 1) / ESCALATE (round 2).
- Any `UNRESOLVED` review comment from a human author → REROLL (round 1) / ESCALATE (round 2).
- Any `UNRESOLVED` review comment from `/review-pr` labelled severity ≥ medium →
  REROLL (round 1) / ESCALATE (round 2).
- Any `NOT_APPLIED` must-fix simplify finding without rationale → REROLL (round 1) /
  ESCALATE (round 2).
- Any `blocking` adherence violation → REROLL (round 1) / ESCALATE (round 2).
- All lists empty AND all criteria ADDRESSED → APPROVED.

If `round == 2` and any trigger fires → upgrade to ESCALATE. Never a third round.

## Anti-patterns the gate refuses to indulge

| Pattern | Why it fails |
|---------|--------------|
| "Test suite passes" as sole evidence | No link from test to criterion; tests could pre-exist |
| "Simplify ran, no findings" | Simplify finds nits, not ticket completion; orthogonal |
| "Reviewer concern filed as follow-up" with no ticket ID | Unverifiable; ticket must exist |
| "Addressed in PR body" without commit | PR body is narrative; need the actual change |
| "Edge case out of scope" without Scope audit confirmation | The Scope phase is Phase 7; gate cannot waive unilaterally |

## Standalone invocation

`/verify-gate <pr-number>` can be called without `/verify` having run first. In that mode
the gate uses only existing PR state (comments, commits, reviews) — no phase 2–5 outputs.
This is useful for sanity-checking a PR the human is considering, or for re-running the
gate after manual fixes.

Standalone mode is always **round=1** regardless of history. The retry-budget semantics
apply only when called from `/verify`.

## Output destinations

1. Structured verdict returned to the caller (for `/verify` consumption).
2. A PR comment posted with a human-readable summary of the verdict. Template:

   ```
   /verify-gate round=<n> verdict=<V>

   Exit criteria: <n_addressed>/<n_total> addressed
   Review comments: <n_unresolved> unresolved
   Simplify: <n_unresolved> must-fix not applied
   Adherence: <n_blocking> blocking violations

   Top reasons (if not APPROVED):
   - <ranked list>

   Rationale: <paragraph>
   ```

## Circuit breakers

- Ticket cannot be located → ESCALATE (no blind approval).
- PR body lacks test plan → not a gate-level failure, but recorded as a nit.
- Gate cannot access commit timestamps → ESCALATE (cannot distinguish pre/post comment changes).
- Contradictory signals between phases 2–5 → ESCALATE (no silent resolution).

## Not in scope

- **Merging.** The gate never calls `gh pr merge`.
- **Re-running tests.** The gate reads results; phase 1 of `/verify-adherence` runs them.
- **Scope audit.** That's Phase 7 of the orchestrator, handled separately.
