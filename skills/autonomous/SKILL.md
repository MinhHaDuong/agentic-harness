---
name: autonomous
description: Launch unsupervised autonomous session. Works in Imperial Dragon cycles with deliverable-first balance.
disable-model-invocation: true
user-invocable: true
argument-hint: [territory]
model: claude-opus-4-6
effort: max
---

# Autonomous exploration session

Unsupervised session — work autonomously, review your own PRs, push forward on deliverables. Author reviews results when the session ends.

## Balance rule

**Deliverable work ≥60%, tooling ≤40%.** If two consecutive tickets were tooling, the next must advance a deliverable. Track in session log.

**Deliverables**: items in `STATE.md` under current milestone — papers, slides, reading notes, figures, responses to reviewers. Tooling: tests, hygiene, refactoring, harness improvements.

**Escape hatch**: if `make check-fast` fails and blocks all deliverable work, tooling may exceed 40%. Document why.

## Procedure

Loop of Imperial Dragon cycles: Imagine → Plan → Execute → Verify → Celebrate. Keep cycling until wrap-up time.

### Picking targets (per cycle)

1. Scientific deliverable is paramount
2. Resolve gaps with north star (STATE.md)
3. Fix ripest open issues
4. Sweep for inline markers (FIXME, TODO, HACK)

### Bootstrap

Run session start setup. Record start time. Read territory files. Run `make check` as baseline.

### Deliverable work

For papers: analyze findings → survey journals → match → outline → draft → review literature → iterate.

### Tooling tickets

TDD in worktrees. Self-review (single agent, correctness focus). Max 4 active worktrees.

### Competing explorations

Up to 3 implementations in parallel for each idea.

### Mid-session checkpoint (~50% effort)

- [ ] Opened at least one deliverable-forward PR?
- [ ] Tooling/deliverable ratio within bounds?
- [ ] Self-reviewed at least one PR?
- [ ] `make check` passes on main?

### Wrap up

1. `make check` on main — compare against baseline. New failures → ticket.
2. Clean up worktrees.
3. All work pushed, PRs open.
4. Write briefing (session log + PR list + test delta).
5. Do NOT run `/end-session` (would re-trigger autonomous).

## Invariants

- **Never merge to main.** All changes as PRs.
- **One ticket per worktree.**
- **Commit messages explain why.**

## Anti-patterns

- Entire session on tooling, zero deliverable progress.
- Did not self-review PRs.
- Did not recurse into new dreams after completing existing ones.
- Moved failing tests out of sight instead of fixing.
