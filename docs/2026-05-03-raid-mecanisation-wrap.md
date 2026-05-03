# Raid mecanisation — wrap-up — 2026-05-03

Final scoreboard for the mecanisation sweep raid. All work pushed; all
PRs open and awaiting author review.

## Scoreboard

| Ticket | PR | Title | Status | Tests |
|---|---|---|---|---|
| 0042 | [#87](https://github.com/MinhHaDuong/ImperialDragonHarness/pull/87) | Replace harness-rules with index-based lazy load | open | 96 pass |
| 0049 (Tier 2) | [#89](https://github.com/MinhHaDuong/ImperialDragonHarness/pull/89) | Lightweight exit-criteria check + `CLOSED:` repick loop | open | 103 pass |
| 0051 (Layer 0) | [#88](https://github.com/MinhHaDuong/ImperialDragonHarness/pull/88) | Move cooldown-recent-pick guard to beat.py | open | 101 pass |
| 0043 | [#90](https://github.com/MinhHaDuong/ImperialDragonHarness/pull/90) | Weekly /fewer-permission-prompts via nightbeat | open | 107 pass |
| 0073 | [#86](https://github.com/MinhHaDuong/ImperialDragonHarness/pull/86) | hasBranch unit tests | open | go test green |

Five PRs, all CLEAN scope-audit verdicts, no follow-up tickets demanded
by scope creep.

## Recommended merge order

Per Phase 6 integration review:
**#86 → #87 → #88 → #90 → #89.**

Rationale: #89 contains the largest structural change (`_raid()`
single-call → bounded `while` loop), so it rebases against everything
else once instead of forcing each downstream PR to rebase against it.
The known mechanical conflicts (`scripts/beat.py` `_raid()`,
`skills/pick-ticket/SKILL.md` cooldown paragraph,
`tests/test_beat.py` EOF append, `STATE.md` adjacent line removals)
all resolve cleanly under this order.

## Bump tally

Across 73 active tickets prior to this raid:

```
2 verify-reroll
2 permission
1 verb (legacy / unknown-category placeholder)
```

No new bumps from raid-spawned agents — all five Wave 1 agents
completed their TDD red→green cycle without escalation.

## Follow-up tickets recommended

- **ticket-close: accept optional reason argument** — small. Removes
  the hand-written `sweep-close: already-done` log line that #89's
  pick-ticket currently writes itself because `/ticket-close <id>`
  doesn't accept a reason parameter. Layering wart, easy fix.

Existing tickets that remain open as planned:
- **0049** stays open with Tier 2 marked done; Tier 1 (housekeeping
  integration) remains under ticket 0034.
- **0051** stays open with Layer 0 marked done; Layers 1 (cross-project
  IDLE fallback) and 2 (pre-flight no-change skip) deferred.
- **0057, 0059** — still blocked on git-erg exposing mutation commands
  (`erg close`, `erg log`, `erg pick --json`, `erg pick-record`).

## Test delta

Pre-raid: ~96 pytest + existing Go tests on main.
Post-raid (each PR independent against main):

- #86 adds 4 Go tests (hasBranch coverage)
- #87 adds 1 bash test (`tests/test_harness_rules_injection.sh`)
- #88 adds 5 pytest tests (3 helper + 2 _raid integration)
- #89 adds 7 pytest tests (4 parse_pick + 3 raid loop)
- #90 adds 11 pytest tests (4 beat + 4 helper + 3 nightbeat-report)

If all five land cleanly: ~30 net new tests. No CI guard regressions
reported by any agent (`leak-guard`, `pipefail-guard`, `skill-lint`,
`erg validate` all green per-worktree).

## Artifacts

- `docs/2026-05-03-raid-mecanisation.md` — Phase 1-4 briefing (sweep,
  imagine, plan, feasibility)
- `docs/2026-05-03-raid-mecanisation-phase6-7.md` — Phase 6/7 review
  (scope audit + integration findings + merge order)
- `docs/2026-05-03-raid-mecanisation-wrap.md` — this file
- Branch `claude/sweep-orchestrate-tickets-UAb3g` — orchestration
  metadata only; no executable changes here. Each PR carries its own
  ticket's diff.

## Worktree note

`Agent(isolation:"worktree")` worktrees are still locked under
`.claude/worktrees/`. Per `STATE.md` they are harness-managed; do not
remove manually.

## What did NOT happen

- **Per-PR `/verify` (Phase 6 first half).** This raid ran the per-wave
  integration check and the scope audit but did not invoke the full
  `/verify` pipeline (`/verify-adherence`, `/review`, `/review-pr`,
  `/simplify`, `/verify-gate`) on each PR. Reason: `/verify` is a
  project-local skill not loadable as a slash command from this
  remote-orchestration session. Author runs `/verify <pr>` locally per
  the standard interactive flow before merging.
- **No merges.** Per the raid contract: the raid never merges. Each PR
  awaits author review.
