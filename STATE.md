# Imperial Dragon Harness — State

Last updated: 2026-04-26 (nightbeat-report, beat fixes)

## North star

A reusable, science-backed personal harness for AI-assisted research: code and prose, day and night, across projects and machines.

## Status

Level 4 (Hooks) + orchestrator + `/verify` loop + git-erg tickets + bibliography pipeline all shipped. Skills slimmed to non-obvious constraints only. Shell init harness-tracked (`scripts/shell-init.sh`). CI live on main: validate-tickets + skill-lint + leak-guard + pipefail-guard.

**Forge-agnostic**: leak-guard enforces no `gh`/`github.com` in skills. Coding rules (coding-python.md) loaded conditionally for Python projects only.

**Nightbeat** (`claude-nightbeat.timer`) live on padme. Fires hourly 22:00–06:00 weeknights, all day weekends. `beat.py` hardcodes control flow (pick→orchestrate) in Python — no LLM orchestrator. Per-project lock allows concurrent beats on different projects. `project_scoped=True` on pick-ticket/orchestrator prevents cross-project ticket leakage. Orchestrator can now push branches and open PRs (push guard removed from `beat-settings.json`). Housekeeping budget raised to $0.35. `_cleanup_stale_in_progress()` runs at beat startup to rewrite buried orphan records. 60 pytest tests, ruff-clean.

**Morning review**: `/nightbeat-report` skill runs `scripts/nightbeat-report.py`, narrates completed work, lists branches to push, and surfaces harness friction patterns.

**git-erg**: pre-commit hooks installed in all four projects (aedist-technical-report, cadens, Climate_finance, fuzzy-corpus). `erg` binary present in all four.

## Open tickets (1)

- 0013 — bib-to-zotero (push refs.bib to Zotero via API at submission)

## Blockers

None

## Next actions

- Morning review: `/nightbeat-report` — runs the parser and narrates overnight work
- **doudou setup**: add source line to `~/.bashrc`, install nightbeat systemd units, copy erg binary to all projects
- Implement ticket 0027 (pick-ticket incremental assessment + `sweep-skip` verb) — annotated with post-talk case
- Build 0013 (bib-to-zotero) when a manuscript reaches submission

## Backlog

- When beat do nothing, immediately redo with next project
- Streamline settings.json hook configuration
- Actually make use of the built-in self-monitoring
- Merge REALF guidelines and business rules
- Enable branch protection requiring `validate-tickets` on main
