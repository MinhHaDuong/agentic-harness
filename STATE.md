# Imperial Dragon Harness — State

Last updated: 2026-04-25 (beat.py — per-project lock + erg hooks)

## North star

A reusable, science-backed personal harness for AI-assisted research: code and prose, day and night, across projects and machines.

## Status

Level 4 (Hooks) + orchestrator + `/verify` loop + git-erg tickets + bibliography pipeline all shipped. Skills slimmed to non-obvious constraints only. Shell init harness-tracked (`scripts/shell-init.sh`). CI live on main: validate-tickets + skill-lint + leak-guard + pipefail-guard.

**Forge-agnostic**: leak-guard enforces no `gh`/`github.com` in skills. Coding rules (coding-python.md) loaded conditionally for Python projects only.

**Nightbeat** (`claude-nightbeat.timer`) live on padme. Fires hourly 22:00–06:00 weeknights, all day weekends. `beat.py` hardcodes control flow (pick→orchestrate) in Python — no LLM orchestrator. Per-project lock (`nightbeat-{name}.lock` under `$XDG_RUNTIME_DIR`) allows concurrent beats on different projects. `project_scoped=True` on pick-ticket/orchestrator prevents cross-project ticket leakage. 60 pytest tests, ruff-clean.

**git-erg**: pre-commit hooks installed in all four projects (aedist-technical-report, cadens, Climate_finance, fuzzy-corpus). `erg` binary present in all four.

## Open tickets (1)

- 0013 — bib-to-zotero (push refs.bib to Zotero via API at submission)

## Blockers

None

## Next actions

- Monitor nightbeat runs: `journalctl --user -u claude-nightbeat.service -f` and per-project `beat-log.jsonl`
- **doudou setup**: add source line to `~/.bashrc`, install nightbeat systemd units, copy erg binary to all projects
- Build 0013 (bib-to-zotero) when a manuscript reaches submission

## Backlog

- Streamline settings.json hook configuration
- Actually make use of the built-in self-monitoring
- Merge REALF guidelines and business rules
- Enable branch protection requiring `validate-tickets` on main
