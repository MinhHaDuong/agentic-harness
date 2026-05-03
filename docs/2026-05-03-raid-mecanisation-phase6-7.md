# Raid mecanisation — Phase 6/7 review (Wave 1) — 2026-05-03

Per-PR scope audit (Phase 7) and per-wave integration review (Phase 6)
across the 5 parallel PRs (#86–#90) opened off
`claude/sweep-orchestrate-tickets-UAb3g`.

## 1. Per-PR scope verdict

| PR  | Ticket          | Verdict | Notes |
|-----|-----------------|---------|-------|
| #86 | 0073            | CLEAN   | Single-file diff to `tickets/tools/go/main_test.go`. Adds `runGit` + `newGitRepo` helpers and 4 tests (local match, local no-match, remote match, offline fallback). `hasBranch` itself is **not** refactored — Phase 3's tentative `cmd.Dir` refactor was correctly skipped; agent serialised via `os.Chdir` + `t.Cleanup` instead. |
| #87 | 0042            | CLEAN   | Touches loading mechanism only (new `README.md` index, `cat` line in `on-start.sh`, deletion of `SKILL.md`, top-level README + STATE doc edits, new test). No rule-body content modified — the bodies of `workflow.md` / `git.md` / `coding-python.md` / `state.md` / `tickets.md` are untouched. |
| #88 | 0051 (Layer 0)  | CLEAN   | Strictly Layer 0: `_ticket_recently_picked()` helper + call site in `_raid()` + cooldown prose removal at `skills/pick-ticket/SKILL.md`. No project rotation (Layer 1) and no pre-flight no-change skip (Layer 2). |
| #89 | 0049 (Tier 2)   | CLEAN   | Stays inside Tier 2: `parse_pick` tuple, `CLOSED:` repick loop with `MAX_CLOSED_REPICKS=3`, new SKILL step 4. Tier 1 (housekeeping integration) and Tier 3 (start-ticket exit verify) untouched. The Phase 4 workaround (write own `sweep-close: already-done` log line because `/ticket-close` does not accept a reason arg) is correctly implemented. |
| #90 | 0043            | CLEAN   | Read-only: helper writes diffs to `~/.claude/telemetry/permission-diffs/<date>.diff`, never auto-applies. `_prune_permissions` swallows all exceptions (`# noqa: BLE001`) so beat keeps running. Reasonable scope creep into `nightbeat-report.py` to surface diffs is required by Phase 3 plan. |

All five PRs **CLEAN**. No follow-up tickets demanded by scope creep.

## 2. Wave-level integration findings

- **`scripts/beat.py` — 3-way insertion in `_raid()`.** PRs #88, #89, #90
  all modify the body of `_raid()` immediately after the housekeeping
  guard. Per the Phase 4 plan the three insertion sites were said to be
  line-disjoint; in practice #88 inserts the cooldown guard, #90 inserts
  `_prune_permissions(path)`, and #89 rewrites the entire pick-ticket
  block (single-call → bounded while-loop). git's 3-way merge will most
  likely auto-merge **#88 + #90** (different inserted blocks at adjacent
  but distinct lines) but **will conflict on #89 ↔ either** because #89
  rewrites the same hunk that #88/#90's contexts include. Empirical
  conflict zone: lines ~820–870 of post-merge `beat.py`.
- **`scripts/beat.py` — `parse_pick` consumer at line 819.** Only #89
  touches `parse_pick`. Neither #88 nor #90 reference `parse_pick` or
  `ticket_id` from its old return shape, so the type change does not
  silently break their hunks.
- **`scripts/beat.py` — `timedelta` import.** #88 adds `timedelta` to
  `from datetime import datetime, timezone`. #89 does NOT add it (the
  `MAX_CLOSED_REPICKS` loop uses no time math). #90 does not add it
  either. So the import diff is single-source from #88 and will not
  collide.
- **`tests/test_beat.py` — `from datetime import …, timedelta, …` at
  line 8.** #88 adds this; the existing import line currently lacks
  `timedelta`. #89/#90 do not add this import, so single-source again,
  no dedup needed.
- **`tests/test_beat.py` — append at EOF.** Both #88 and #90 append a
  new test class after the existing line 1185. This is the classic
  "two patches both adding to the bottom" case — git will auto-merge
  iff the old final line is identical context for both patches; in
  practice this **usually** works but a manual review is wise.
- **`tests/test_beat.py` — `TestParsePick`.** #89 modifies every
  existing case in lines 47–89. Neither #88 nor #90 touch this class,
  so #89's hunk is line-disjoint from the others.
- **`skills/pick-ticket/SKILL.md` — section overlap.** #89 inserts a
  brand-new step 4 ("Lightweight exit-criteria check") and renumbers
  the rank/beat-skip/idle steps to 5/6/7. #88 modifies the body of the
  old step 5 (now step 6 under #89's renumbering): deletes the
  `Always add a cooldown entry … {now+8h} …` paragraph and replaces it
  with a one-liner pointing at `_ticket_recently_picked()`. **This is a
  guaranteed conflict** — both PRs touch the same paragraph and #89's
  patch context still contains the old cooldown prose that #88 deletes.
  The conflict is benign (the resolution is mechanical: keep #89's new
  step 4, keep #88's beat-skip rewording at step 6, drop the old
  `{now+8h}` paragraph) but it is **not** auto-mergeable.
- **`skills/pick-ticket/SKILL.md` — description line.** #89 also
  rewrites the frontmatter `description:` to mention `CLOSED:`. #88 does
  not touch frontmatter, so no collision there.
- **STATE.md — adjacent line removals.** #87 deletes the `0042` line,
  #90 deletes the `0043` line. They are adjacent in the Open tickets
  list. git will auto-merge as long as both deletions still resolve
  against the surrounding context (they should — different anchor
  lines).
- **README.md.** #87 edits the `harness-rules/` block in the structure
  diagram (lines 19–24). #90 adds a new `## Permissions` section much
  further down (around line 130). Line-disjoint.
- **Imagined merge of #88 + #89 (riskiest pair).** Resolving the SKILL.md
  conflict and the `_raid()` conflict by hand: the resulting `_raid()`
  would have, in order: (1) housekeeping guard, (2) cooldown
  short-circuit (#88), (3) prune-permissions call (#90, if also
  merged), (4) the bounded while-loop pick-ticket block (#89). Tests
  pass logically: #88's cooldown test mocks `housekeeping_needed`
  False, asserts `outcome == "idle"` and pick-ticket never invoked —
  unaffected by #89's loop because the cooldown short-circuits before
  pick-ticket is reached. #89's loop tests put no recent-pick log in
  `tmp_project`, so #88's cooldown is False and the loop runs as
  expected. **Logically clean.**

## 3. Recommended merge order

To minimise rebase work:

1. **#86** — no collisions with anyone; merge first.
2. **#87** — only touches files no other PR touches (apart from the
   1-line STATE.md removal it shares with #90, which is line-disjoint
   from #87's own STATE.md line). Merge second.
3. **#88** — merge third. Adds the `timedelta` import + the
   `_ticket_recently_picked` helper + the cooldown short-circuit.
   `tests/test_beat.py` gains the import and one tail-append.
4. **#90** — merge fourth. Insert `_prune_permissions` definition above
   `_raid` and the call site below #88's cooldown short-circuit. The
   tail-append to `tests/test_beat.py` will need a trivial rebase
   against #88's tail-append. STATE.md `0043` line: rebase against #87's
   `0042` removal — context shifts by one line, git handles
   automatically.
5. **#89** — merge **last**. By the time #89 rebases, `_raid` will have
   the cooldown guard and the `_prune_permissions` call already in
   place, so #89's rewrite of the pick-ticket block has a clean,
   well-defined insertion point. The SKILL.md conflict against #88
   becomes a clean rebase: #88's rewording of the beat-skip paragraph
   is already on `main`, and #89 simply inserts a new step 4 above it
   and renumbers down.

Rationale: #89 is the largest structural change to `_raid`, so it
rebases against everything else rather than having everything else
rebase against it. SKILL.md is rebased once (during #89's rebase) rather
than twice.

## 4. Outstanding follow-ups

- **`/ticket-close` should accept a reason argument.** Per the Phase 4
  workaround, #89's pick-ticket now writes its own
  `sweep-close: already-done hash:<…>` log line because `/ticket-close`
  has no reason parameter. This is a layering wart — pick-ticket and
  ticket-close together know how to close, but the structured-reason
  bit lives only in pick-ticket prose. **Recommend opening a ticket**:
  "ticket-close: accept optional reason argument and emit it in the
  status log line." Estimate: small.
- **`MAX_CLOSED_REPICKS` bound.** The Phase 4 deferral noted that the
  bound (3) is somewhat arbitrary versus 1. Consider tightening to 1
  after observing real-world behaviour for a week — either via a
  follow-up ticket or by leaving it as a settings.json knob.
- **Layer 1 + Layer 2 of 0051** (cross-project IDLE fallback,
  pre-flight no-change skip) remain open as planned. No new ticket
  needed; existing 0051 stays open with Layer 0 marked done in its log.
- **Tier 1 of 0049** (housekeeping integration) remains open under
  ticket 0034 as planned. No action needed.
- **`anthropics/claude-code#51057`** (env-var prefix stripping) is
  documented in #90's helper header but not tracked here as a ticket —
  it is upstream. Acceptable.
- **Empirical verification of `--non-interactive` fallback.** #90
  reports the fallback works against `claude` 2.1.126; should be
  re-verified after the next CLI bump. Not ticket-worthy on its own.
- **No raid-orchestration ticket needed for the 3-way `_raid` merge
  conflict.** The conflict is mechanical and the recommended merge
  order eliminates it.

## 5. Summary

Wave 1 of the mecanisation raid landed five well-scoped PRs with no
agent scope creep. Three of them (0049, 0051, 0043) collide in
`scripts/beat.py` `_raid()` and in `tests/test_beat.py`, and two of
them (0049, 0051) collide on the same paragraph of
`skills/pick-ticket/SKILL.md`; the collisions are resolvable by hand
in roughly five minutes given the recommended merge order
(#86 → #87 → #88 → #90 → #89). The riskiest imagined-merge pair (#88 +
#89) is logically clean — their tests are independent and would still
pass once the textual conflicts are resolved. One follow-up ticket is
recommended: extend `/ticket-close` to accept a reason argument so
pick-ticket no longer has to hand-write its own
`sweep-close: already-done` log line.
