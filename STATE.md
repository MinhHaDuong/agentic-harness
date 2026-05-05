# Imperial Dragon Harness — State

Last updated: 2026-05-05T14:45Z

## North star

A reusable, science-backed personal harness for AI-assisted research: code and prose, day and night, across projects and machines.

## Status

Level 4 (Hooks) + raid + `/verify` loop + git-erg tickets + bibliography pipeline all shipped. Skills slimmed to non-obvious constraints only. Shell init harness-tracked (`scripts/shell-init.sh`). CI live on main: validate-tickets + skill-lint + leak-guard + pipefail-guard.

**Forge-agnostic**: leak-guard enforces no `gh`/`github.com` in skills.

**Nightbeat** (`claude-nightbeat.timer`) live on padme. Fires every 30 min 22:00–06:00 weeknights, every 30 min all day weekends (17 runs/night). `beat.py` controls flow in Python — no LLM orchestrator. Per-project lock allows concurrent beats. `project_scoped=True` prevents cross-project ticket leakage. Beat prints one-line run summary to stdout (project, ticket, outcome, duration).

**Per-project budgets**: `ProjectConfig` dataclass in `beat.py` — all projects at $0.40/$0.50. 2 targets in `scripts/projects.json`: `aedist-technical-report`, `~/.claude`. Ticket 0069 open to move config into per-project `.claude/beat.json`.

**Idle skip**: housekeeping skipped when repo has no commits since last run (ticket 0036 closed).

**Token economy** (PR #97, 2026-05-04): deterministic skill steps extracted to scripts — `scripts/smoke.sh`, `scripts/bib-merge.py`, `scripts/validate-refs.py`. Skills now make 1 Bash call for mechanical work; LLM handles only non-deterministic steps. `erg validate <files>` (not directory) used at all call sites; `erg check tickets/` added to housekeeping with graceful fallback pending git-erg/0038.

**Project state probe** (PR #100, 2026-05-05): `scripts/project-state.py <path> [--full]` — mechanical per-project JSON probe (git status, housekeeping state, ticket counts; full mode adds tests + PRs). Pure stdlib, exit 0 always. `/healthcheck` skill now calls it as its data-collection step. Foundation for upcoming `/eyes` multi-project survey.

**Beat outcome instrumentation** (PR #101, 2026-05-05): `run_skill()` now returns `_SkillResult` (subtype, permission_denials, cost_usd, is_error). `_record_phase_outcome()` appends one JSONL record per phase to `~/.claude/logs/beat-outcomes.jsonl` — housekeeping (idle/success/timeout/fail), pick_ticket (idle/skip/timeout/fail), raid (success/budget/timeout/fail). Budget detected via `error_max_budget_usd` subtype. `nightbeat-report.py` shows 7-day phase outcome table and surfaces denial/budget events.

**git-erg**: pre-commit hooks installed in all projects. CI live (ticket 0009, PR #4 merged). Validation split: `erg validate <files>` (per-file) vs `erg check [dir]` (corpus) defined in spec; binary implementation tracked by git-erg/0038.

**Worktree lifecycle**: worktrees created via `Agent(isolation:"worktree")` are harness-managed. Skills must not rm them manually. Raid wrap-up step "Clean up worktrees" removed (2026-04-30).

## Open tickets

- 0013 — bib-to-zotero (push refs.bib to Zotero via API at submission)
- 0017 — bump verb instrumentation in erg validator + skills
- 0026 — clarify Phase 7 scope-creep handling
- 0027 — pick-ticket incremental assessment cache
- 0028 — multiproject beat dashboard (Views 1-2)
- 0029 — beat dashboard blocker graph (blocked by 0028)
- 0031 — housekeeping: replace grep-based scan with `erg ready --json`
- 0034 — housekeeping: split git-cleanup and ticket-scan into two phases
- 0044 — interactive session observer
- 0047 — auto early context compaction in beat and raid
- 0051 — beat should try another project when current one is idle or frozen
- 0057 — route .erg mutations through erg binary (blocked: needs git-erg/0039 `erg log` + git-erg/0040 `erg new`)
- 0061 — sequence parallel agents to stay under budget (corpus discovery fanout crash)
- 0062 — run nightbeat from a VM (uptime + bypass Gallica 403 blocks)
- 0063 — enforce erg source read-only in IDH; edits go to git-erg
- 0064 — audit bash/permission denial patterns across last 3 nights
- 0065 — /nightbeat-risk-review skill (interactive log triage before next night)
- 0067 — rename celebrate→roar and end-session→lair (blocked by 0068)
- 0068 — two-word canonical names + IDH aliases for all skills
- 0069 — per-project beat config (.claude/beat.json) with interval_minutes
- 0070 — /dream skill — autonomous nightly memory consolidation
- 0084 — cheap-worker delegation (blocked: needs WORKER_API_KEY + openai library)
- 0054 — [discussion] restore Five-Claws phase announcement at session start
- 0055 — [discussion] milestone/epic layer above tickets
- 0056 — [discussion] mid-session pause/resume checkpoints

## Blockers

- **0057**: needs git-erg/0039 (`erg log`) + git-erg/0040 (`erg new`) in binary
- **0084**: needs WORKER_API_KEY secret + openai library on host

## Next actions

- **doudou setup**: add source line to `~/.bashrc`, install nightbeat systemd units, copy erg binary to all projects
- **git-erg/0008**: rewrite branch-as-claim check in `erg ready` — pending from git-erg session (IDH hook reverted IDH-side edits twice)

## Backlog

- Streamline settings.json hook configuration
- Enable branch protection requiring `validate-tickets` on main
- Merge REALF guidelines and business rules
