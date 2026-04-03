# Imperial Dragon Harness

User-level Claude Code harness for Minh Ha-Duong's research workflow.

## The Five Claws

Every task passes through five phases:

| Claw | Phase | Activity |
|------|-------|----------|
| 1 | **Imagine** | Explore, brainstorm, surface motivations |
| 2 | **Plan** | Design, write tickets with test specs |
| 3 | **Execute** | TDD red/green/refactor, open PR |
| 4 | **Verify** | Review PR, fix, iterate ≤3 cycles |
| 5 | **Celebrate** | Reflect, consolidate memory, dream forward |

## Directory layout

```
~/.claude/
├── rules/          # Always-loaded behavioral rules
│   ├── git.md          # Git discipline (branch, commit, worktree)
│   ├── workflow.md     # Session start, escalation, phase transitions
│   ├── coding.md       # Python style, testing, Make patterns
│   └── state.md         # STATE.md spec
├── skills/         # On-demand slash commands
│   ├── celebrate/      # Post-task wrap-up
│   ├── end-session/    # Day wrap-up
│   ├── memory/         # Persistent memory management
│   ├── new-ticket/     # GitHub issue template
│   ├── start-ticket/   # Begin work on issue (TDD)
│   ├── review-pr/      # Multi-agent code review
│   ├── review-pr-prose/ # Peer review panel for prose
│   └── autonomous/     # Unsupervised exploration session
├── hooks/          # Lifecycle scripts
│   └── on-start.sh     # Session start: identity, env, hooks
├── commands/       # Custom slash commands
│   └── choose-journal.md
├── docs/           # Reference material
│   ├── 5 levels of harnessing.md
│   ├── Forsythe-2026-10principles.odt
│   ├── braindump-harness-extraction.md
│   ├── VISION-original.md
│   └── telemetry-scripts/
├── settings.json   # Permissions, hooks (not tracked)
└── .gitignore      # Track only harness components
```

## How it works

Claude Code loads user-level (`~/.claude/`) and project-level (`.claude/`) config automatically. Precedence:

- **Rules**: project overrides user (project adds specifics on top of generic)
- **Skills**: user overrides project (generic skills serve as defaults)
- **Hooks**: both run (most restrictive decision wins)
- **Settings**: scalars — project wins; arrays — merge

Projects add their own rules, hooks, and project-specific skills. The harness provides the workflow skeleton.

## Backed by

https://github.com/MinhHaDuong/ImperialDragonHarness
