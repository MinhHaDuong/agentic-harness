# Imperial Dragon Harness — State

Last updated: 2026-04-24

## North star

A reusable, science-backed personal harness for AI-assisted research: code and prose, day and night, across projects and machines.

## Status

Level 4 (Hooks) + orchestrator + `/verify` loop + git-erg tickets + bibliography pipeline all shipped. Skills slimmed to non-obvious constraints only. Shell init harness-tracked (`scripts/shell-init.sh`). CI live on main (validate-tickets + skill-lint + leak-guard + pipefail-guard). Harness-rules now cover build structure: split by workpackage, commit handoff artifacts. Forge-agnostic: leak-guard enforces no `gh`/`github.com` in skills; verify skills and coding rules decoupled from stack assumptions.

Field testing on a handful of projects: data analysis in Python and academic writing in LaTeX and QMD. Four projects have ticketed split-build work (Cadens 0022, Fuzzy Corpus 0023, AEDIST 0112, Climate Finance 0093).

## Open tickets (5)

- 0013 — bib-to-zotero (push refs.bib to Zotero via API at submission)
- 0018 — shell-pipefail-guard — **PR #56 open, approved**
- 0020 — forge-agnostic verify skills — **PR #57 open, approved**
- 0021 — verify-adherence stack-agnostic adapter — **PR #58 open, approved** (depends on #57)
- 0022 — coding.md → coding-python.md scope guard — **PR #55 open, approved**

## Blockers

None

## Next actions

- **Merge PRs**: #55, #56 independent; then #57, then #58 (depends on #57).
- **doudou setup**: add source line to `~/.bashrc` after pulling harness.
- **Project split-build tickets**: commit the four project-side `.erg` files and open PRs.
- Build 0013 (bib-to-zotero) when a manuscript reaches submission.
- Enable branch protection requiring `validate-tickets` on main.

## Backlog

- Streamline settings.json hook configuration (#23)
- Install the daily systemd harness update on all machines
- Actually make use of the built-in self-monitoring
- Merge REALF guidelines and business rules
