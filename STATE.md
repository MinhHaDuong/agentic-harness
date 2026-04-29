# Imperial Dragon Harness — State

Last updated: 2026-04-29T00:00Z

## North star

A reusable, science-backed personal harness for AI-assisted research: code and prose, day and night, across projects and machines.

## Status

Level 4 (Hooks) + raid + `/verify` loop + git-erg tickets + bibliography pipeline all shipped. Skills slimmed to non-obvious constraints only. Shell init harness-tracked (`scripts/shell-init.sh`). CI live on main: validate-tickets + skill-lint + leak-guard + pipefail-guard.

**Forge-agnostic**: leak-guard enforces no `gh`/`github.com` in skills.

**Nightbeat** (`claude-nightbeat.timer`) live on padme. Fires hourly 22:00–06:00 weeknights, all day weekends. `beat.py` controls flow in Python — no LLM orchestrator. Per-project lock allows concurrent beats. `project_scoped=True` prevents cross-project ticket leakage.

**Per-project budgets**: `ProjectConfig` dataclass in `beat.py` — aedist-technical-report, cadens, harness at $0.40/$0.50; Climate_finance, fuzzy-corpus at $0.75/$0.75.

**Idle skip**: housekeeping skipped when repo has no commits since last run (ticket 0036 closed).

**erg sweep cache**: `erg ready --json` returns `cache`/`hash`/`scope`/`risk` per ticket. `erg sweep-skip` and `erg sweep-write` compute hash server-side. Pick-ticket reads ticket bodies only on cache:miss. 62 pytest + 24 Go tests, all green.

**git-erg**: pre-commit hooks installed in all four projects. `erg` binary present in all four.

## Open tickets

- 0013 — bib-to-zotero (push refs.bib to Zotero via API at submission)
- 0028 — multiproject beat dashboard (Views 1-2)
- 0029 — beat dashboard blocker graph (blocked by 0028)
- 0034 — housekeeping: split git-cleanup and ticket-scan into two phases
- 0037 — fix beat double-pick (raid rc=0 without closing ticket)
- 0038 — use Haiku for pick-ticket when repo has no recent commits
- 0039 — remove/replace git fsck --unreachable in housekeeping
- 0040 — skip housekeeping when repo is frozen (overlaps with 0036 — verify scope)
- 0041 — investigate mid-session context reset between sub-skills
- 0042 — replace harness-rules with hooks (metaskill panorama finding)
- 0043 — weekly /fewer-permission-prompts run
- 0044 — interactive session observer
- 0046 — extract flying-projects list into projects.json
- 0047 — auto early context compaction in beat and raid
- 0057 — route .erg mutations through erg binary (blocked by erg binary exposing mutation commands)
- 0058 — rewrite README with Imperial Dragon voice (remove GSD, new opener)
- 0060 — fix erg sweep-skip slice-aliasing bug + repair 8 corrupted tickets
- 0054 — [discussion] restore Five-Claws phase announcement at session start
- 0055 — [discussion] milestone/epic layer above tickets
- 0056 — [discussion] mid-session pause/resume checkpoints

## Blockers

None

## Next actions

- Morning review: `/nightbeat-report` — runs the parser and narrates overnight work
- Fix 0037 (beat double-pick) — highest operational risk
- Verify 0040 scope vs 0036 — may be redundant; close if so
- **doudou setup**: add source line to `~/.bashrc`, install nightbeat systemd units, copy erg binary to all projects
- Build binary on each machine after erg sweep cache merge (`cd tickets/tools/go && go build -o ../../../bin/erg .`)

## Backlog

- When beat does nothing, immediately redo with next project
- Streamline settings.json hook configuration
- Enable branch protection requiring `validate-tickets` on main
- Merge REALF guidelines and business rules
