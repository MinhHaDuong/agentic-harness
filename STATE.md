# Imperial Dragon Harness — State

Last updated: 2026-04-04

## Status

Review cycle complete. Harness at Level 4 (Hooks). 15 tickets raised, all resolved.

## Blockers

None

## Next actions

- Merge REALF guidelines and business rules
- Implement #23: streamline settings.json hook configuration
- Pull main on ~/.claude to pick up all merged changes
- Apply pruned settings.local.json (docs/20260404-review/settings-local-pruned.json)
- Test new hooks in a real session (lint-on-edit, guard-commit-on-main, check-tests-on-stop)

## North star

A reusable, science-backed harness for AI-assisted research: code and prose, day and night, across projects and machines.

## Current milestone: Self-improvement loop

- [x] Review against references (5 levels, 10 principles, deep research)
- [x] Implement tier 1 fixes (on-start.sh bug, destructive guard, settings audit)
- [x] Implement tier 2 (PostToolUse lint, Stop hook, branch guard, effortLevel)
- [x] Implement tier 3 (telemetry wiring, compaction instruction, staleness warning)
- [x] Clean up docs/ and organize telemetry scripts
- [ ] Merge REALF guidelines and business rules
- [ ] Measure compliance rates (context hygiene, review quality, token economy)

## Backlog

- Streamline settings.json hook configuration (#23)
- Offline ticket system (file-based, gh-optional)
- Multi-machine sync (doudou ↔ padme)
- Second project onboarding (CIRED.digital or activity reports)
