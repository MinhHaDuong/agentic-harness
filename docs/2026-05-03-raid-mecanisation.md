# Raid: mecanisation sweep — 2026-05-03

Briefing for the Imperial Dragon raid against the **mecanisation** ticket
cluster: open tickets whose explicit goal is replacing skill-prose
flowcharts with scripts or `erg` binary commands.

Branch: `claude/sweep-orchestrate-tickets-UAb3g`. Phases 1-4 of the
[raid skill](../skills/raid/SKILL.md) recorded here; Phase 5 (Execute)
spawns per-ticket worktree agents from this briefing.

## Scope

In-scope tickets (run as Wave 1):

| # | Title | Scope |
|---|---|---|
| 0042 | Replace harness-rules with index-based lazy load | SessionStart hook emits index instead of full rule bodies |
| 0049 | Truth in ticket open status | Tier 2 only: pick-ticket grep-based exit-criteria check + `CLOSED:` signal |
| 0051 | Beat idle/frozen project fallback | Layer 0 only: cooldown-recent-pick prose → Python in beat.py |
| 0043 | Weekly /fewer-permission-prompts | Folded into nightbeat (no separate systemd timer) |
| 0073 | hasBranch unit test | 4 test cases in main_test.go with temp-git scaffolding |

Excluded from this raid:

- 0057 (route .erg mutations via erg binary) — blocked on git-erg
  exposing mutation commands
- 0059 (delegate pick-ticket to `erg pick`) — blocked on git-erg/0008
- 0064 (audit denial patterns) — investigative, not mecanisation
- 0034, 0047, 0070 — orthogonal scope
- discussion tickets 0054-0056

## Phase 2: Imagine — scope refinements

- **0049**: ship Tier 2 alone. Tier 1 (housekeeping integration) defers
  to 0034. Tier 3 (start-ticket exit verify) is already in place since
  2026-04-29.
- **0051**: ship Layer 0 alone (pure prose-to-Python lift). Layers 1-2
  defer to a follow-up.
- **0043**: fold into nightbeat — add a `PERMISSIONS_PRUNE_DAY_OF_WEEK`
  config in beat.py rather than a parallel systemd timer. Reuse the
  existing lock and log infrastructure.
- **0042**: 2026-05-03 refined design (index README + SessionStart hook)
  is the right move; resist scope creep into rule content or
  verify-adherence.
- **0073**: surgical fill-in; explicitly test the offline-fallback path,
  not just the happy path.

## Phase 3: Plan — per-ticket actions

### 0042

- **Files**: create `skills/harness-rules/README.md` (index); edit
  `scripts/on-start.sh` to `cat` the index before the `exec >/dev/null`
  cutoff at line 32; delete `skills/harness-rules/SKILL.md`; update
  `README.md` and `STATE.md`.
- **First test**: `tests/test_harness_rules_injection.sh` —
  `test_session_start_emits_index_not_bodies`. Asserts on-start.sh
  output contains rule filenames + scope keywords but NOT rule body
  content.
- **Estimate**: small (~80-120 LOC).

### 0049 (Tier 2)

- **Files**: `scripts/beat.py` (parse_pick → tuple, `_raid()` loop on
  `CLOSED:`); `skills/pick-ticket/SKILL.md` (new step 2.5 with
  exit-criteria checks); `tests/test_beat.py`.
- **Adjustment from Phase 4**: drop the `/ticket-close <id> already-done`
  call. Instead, pick-ticket calls `/ticket-close <id>` and writes its
  own `sweep-close: already-done` log line via the existing log
  mechanism. Loop counter in `_raid()` aborts after 3 consecutive
  `CLOSED:` to prevent infinite loop on flaky exit criteria.
- **First test**: `tests/test_beat.py` —
  `TestParsePick.test_closed_signal_parsing`. Asserts
  `parse_pick("CLOSED: 0049")` returns `("closed", "0049")`.
- **Estimate**: medium (~150-200 LOC).

### 0051 (Layer 0)

- **Files**: `scripts/beat.py` (`_ticket_recently_picked()` helper +
  call site in `_raid()` before pick-ticket); `skills/pick-ticket/SKILL.md`
  (remove cooldown prose at line 61); `tests/test_beat.py`.
- **First test**: `tests/test_beat.py` —
  `TestTicketRecentlyPicked::test_fires_within_8h`. Writes a fresh
  `sweep-pick: picked` log line and asserts the guard returns True.
- **Estimate**: small (~50 LOC).

### 0043

- **Files**: `scripts/beat.py` (`_is_prune_day()` + `_prune_permissions()`);
  new `scripts/fewer-permission-prompts-helper.py` (subprocess wrapper);
  `scripts/nightbeat-report.py` (surface unreviewed diffs);
  `tests/test_beat.py`; `README.md`; `STATE.md`.
- **First test**: `tests/test_beat.py` —
  `TestWeeklyPermissionsPrune::test_prune_skipped_on_non_prune_day`.
  Asserts subprocess is not invoked on a non-prune day.
- **Pre-flight**: helper script `mkdir -p ~/.claude/telemetry/permission-diffs/`.
- **Estimate**: medium (~120-160 LOC).

### 0073

- **Files**: `tickets/tools/go/main_test.go` (4 new tests + temp-git
  scaffolding helper).
- **First test**: `TestHasBranchLocalMatch` — initialise temp git repo,
  create branch `0099-foo`, assert `hasBranch("0099") == true`.
- **Note**: `hasBranch` does not set `cmd.Dir`; tests must use either
  `os.Chdir(tempRepo)` (race-prone in parallel) or run in a goroutine
  with `cmd.Dir` explicitly set in a wrapper. Prefer adding `cmd.Dir`
  in a small refactor of `hasBranch` if scope allows; otherwise
  serialise tests with `t.Setenv("HOME", ...)` and `os.Chdir`.
- **Estimate**: small (~60 LOC).

## Phase 4: Verify feasibility — annotations

| # | Verdict | Notes |
|---|---|---|
| 0042 | PASS | `exec >/dev/null` at line 32, not 31. Otherwise clean. |
| 0049 | BLOCK→workaround | `/ticket-close` skill does not accept a reason argument. Plan adjusted: pick-ticket calls `/ticket-close <id>` plain, writes its own log line. |
| 0051 | PASS | Cooldown prose at `skills/pick-ticket/SKILL.md:61`, removable. |
| 0043 | WARN | `~/.claude/telemetry/` doesn't exist; helper must `mkdir -p`. `/fewer-permission-prompts` is available in current Claude build. Non-interactive mode unverified — helper falls back to piping a confirm-no prompt to stdin. |
| 0073 | PASS | `hasBranch` at lines 579-591 of `tickets/tools/go/main.go`. No git-init helper exists in main_test.go yet; will add. |

**Cross-ticket conflict surface (beat.py)**: 0051 inserts at ~line 805,
0043 inserts at ~line 801, 0049 modifies `parse_pick` at line 367 and
its consumer at line 819. Three insertion sites are line-disjoint;
parallel worktree merges will not conflict at the diff level. Logical
ordering for review: 0051 → 0043 → 0049.

## Phase 5: Execute plan

Wave 1 (all parallel, worktree-isolated):

```
0042  skills/harness-rules/, scripts/on-start.sh, settings.json, README.md
0073  tickets/tools/go/main_test.go
0051  scripts/beat.py (line ~805), skills/pick-ticket/SKILL.md (line ~61)
0043  scripts/beat.py (~line 801), new helper script, scripts/nightbeat-report.py
0049  scripts/beat.py (parse_pick + _raid loop), skills/pick-ticket/SKILL.md
```

Each agent follows `/start-ticket` workflow: read ticket, write red test,
implement, push branch, open PR. The raid never merges — author reviews
each PR.

Phase 6 (per-ticket `/verify`) and Phase 7 (scope audit) run after Wave 1
completes.

## Open Phase 4 verification items deferred to execute

- **0043**: confirm `/fewer-permission-prompts` non-interactive behaviour
  empirically. If it requires interactive stdin, the helper script pipes
  a no-op confirm. If that's still infeasible, escalate.
- **0049**: confirm the loop counter (max 3 consecutive `CLOSED:` per
  beat) is the right bound — could also be 1, given the cost of a false
  positive is just a wasted ticket-close, not budget.
