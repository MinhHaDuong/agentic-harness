# Imperial Dragon Harness — State

Last updated: 2026-04-25 (nightbeat migration + timeout chain overhaul)

## North star

A reusable, science-backed personal harness for AI-assisted research: code and prose, day and night, across projects and machines.

## Status

Level 4 (Hooks) + orchestrator + `/verify` loop + git-erg tickets + bibliography pipeline all shipped. Skills slimmed to non-obvious constraints only. Shell init harness-tracked (`scripts/shell-init.sh`). CI live on main: validate-tickets + skill-lint + leak-guard + pipefail-guard.

**Forge-agnostic**: leak-guard enforces no `gh`/`github.com` in skills; verify/verify-adherence/verify-gate have no forge-specific assumptions. Coding rules (coding-python.md) loaded conditionally for Python projects only. Adherence ratchet protocol is stack-agnostic.

Field testing on a handful of projects: data analysis in Python and academic writing in LaTeX and QMD. Four projects have ticketed split-build work (Cadens 0022, Fuzzy Corpus 0023, AEDIST 0112, Climate Finance 0093).

**Nightbeat** (`claude-nightbeat.timer`) live on padme. Fires hourly 22:00–06:00 weeknights, all day weekends. Timeout chain: bash 52m (primary) → in-progress guard 55m → systemd 57m (last resort). `beat-log.jsonl` per project tracks outcome + `duration_s`.

## Open tickets (1)

- 0013 — bib-to-zotero (push refs.bib to Zotero via API at submission)

## Blockers

None

## Next actions

- Monitor first nightbeat runs (firing hourly today, it's Saturday): `journalctl --user -u claude-nightbeat.service -f` and check per-project `beat-log.jsonl`
- Watch `duration_s` in beat logs to see if 52-min cap is ever hit
- **doudou setup**: add source line to `~/.bashrc` after pulling harness.
- **Project split-build tickets**: commit the four project-side `.erg` files and open PRs.
- Build 0013 (bib-to-zotero) when a manuscript reaches submission.

## Backlog

- Streamline settings.json hook configuration (#23)
- Install nightbeat systemd units + harness on doudou
- Actually make use of the built-in self-monitoring
- Merge REALF guidelines and business rules
- Enable branch protection requiring `validate-tickets` on main
