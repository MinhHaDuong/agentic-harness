# Imperial Dragon Harness — State

Last updated: 2026-04-23

## Status

Level 4 (Hooks) + orchestrator + `/verify` loop + git-erg tickets + bibliography pipeline all shipped. Skills slimmed to non-obvious constraints only. Shell init now harness-tracked (`scripts/shell-init.sh`): sources from `~/.bashrc`, auto-names sessions after project, warns on new machines.

## Open tickets (2)

- 0013 — bib-to-zotero (push refs.bib to Zotero via API at submission)
- 0015 — add CI (validator + skill sanity on PR/push)

## Blockers

None

## Next actions

- **doudou setup**: add source line to `~/.bashrc` after pulling harness
- **CI batch**: 0015 here + git-erg 0003 + AEDIST 0111 + Climate-finance 0081. Once green, enable branch protection.
- Build 0013 (bib-to-zotero) when a manuscript reaches submission.
- Merge REALF guidelines and business rules.

## North star

A reusable, science-backed harness for AI-assisted research: code and prose, day and night, across projects and machines.

## Backlog

- Streamline settings.json hook configuration (#23)
- streamline-onboard branch: open PR pending
- Second project onboarding (CIRED.digital or activity reports)
- Measure compliance rates (context hygiene, review quality, token economy)
