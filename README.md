# Imperial Dragon Harness

A Claude Code harness for Minh Ha-Duong's research workflow. Lives as `~/.claude`.

## The Five Claws

Every task passes through five phases:

| Claw | Phase | Activity |
|------|-------|----------|
| 1 | **Imagine** | Explore, brainstorm, surface motivations |
| 2 | **Plan** | Design, write tickets with test specs |
| 3 | **Execute** | TDD red/green/refactor, open PR |
| 4 | **Verify** | Review PR, fix, iterate ≤3 cycles |
| 5 | **Celebrate** | Reflect, consolidate memory, dream forward |

## Structure

```
ImperialDragonHarness/
├── skills/                 # Slash commands — 21 total: /celebrate, /verify, /orchestrator, etc.
│   ├── harness-rules/      # Auto-invoked rules (companion .md files)
│   │   ├── SKILL.md
│   │   ├── workflow.md         # Session start, escalation, worktree
│   │   ├── git.md              # Branch, commit, PR discipline
│   │   ├── coding-python.md    # Python style, testing, Make (load when Python project)
│   │   ├── state.md            # STATE.md format spec
│   │   └── tickets.md          # Ticket log verbs including bump categories
│   ├── orchestrator/       # Autonomous batch across multiple tickets
│   ├── verify/             # Full PR verification loop (adherence + review + gate)
│   ├── verify-adherence/   # Mechanical rule check on branch diff
│   ├── verify-gate/        # Anti-rubber-stamp merge gate
│   ├── review-pr/          # Multi-agent code review
│   ├── review-pr-prose/    # Peer review panel for prose
│   ├── celebrate/          # Post-task wrap-up
│   ├── end-session/        # Day wrap-up + STATE.md refresh
│   ├── new-ticket/         # Create git-erg ticket with TDD spec
│   ├── start-ticket/       # Begin work on a ticket (TDD red step)
│   ├── ticket-claim/       # Claim a ticket for work (cross-worktree safe)
│   ├── ticket-close/       # Close ticket and release claim
│   ├── ticket-new/         # Low-level: create a raw .erg file
│   ├── ticket-ready/       # List unblocked, unclaimed tickets
│   ├── ticket-release/     # Abandon work, restore ticket to open
│   ├── healthcheck/        # Git hygiene + doc freshness check
│   ├── memory/             # Persistent memory management
│   ├── bib-merge/          # Merge approved bib entries into refs.bib
│   ├── related-work-note/  # Due-diligence note for a cited paragraph
│   └── related-work-note-validate/ # Re-resolve all DOIs/URLs in a note
├── scripts/                # Hook implementations + shell init
│   ├── shell-init.sh           # Source from ~/.bashrc — claude wrapper
│   ├── on-start.sh             # Session start: env loading, worktree gate
│   ├── guard-destructive-bash.sh
│   ├── guard-commit-on-main.sh
│   ├── block-pr-merge-in-worktree.sh
│   ├── lint-on-edit.sh
│   └── warn-stale-rules.sh
├── commands/               # Guidance documents
│   ├── choose-journal.md
│   └── gsd/                    # 33 research workflow commands
├── bin/                    # Utilities (added to PATH)
│   ├── usage-report
│   ├── snapshot
│   └── install-cron
├── settings.json           # Hooks, permissions, env vars
└── docs/                   # Reference material (not loaded)
```

## Installation

1. Clone the repo as your `~/.claude` directory:
   ```bash
   git clone https://github.com/MinhHaDuong/ImperialDragonHarness.git ~/.claude
   ```

2. Create `~/.claude/.env` with your API keys (this file is gitignored):
   ```
   ANTHROPIC_API_KEY=sk-...
   OPENAI_API_KEY=sk-...
   ```

3. Add one line to your `~/.bashrc` (or `~/.zshrc`) to source the harness shell init:
   ```bash
   [ -f "$HOME/.claude/scripts/shell-init.sh" ] && source "$HOME/.claude/scripts/shell-init.sh"
   ```
   This installs a `claude` wrapper that skips permission prompts and auto-names each session after the current git repo. The script lives in the harness, so it updates on every pull.

Skills are available as `/celebrate`, `/review-pr`, etc. Hooks fire automatically via `settings.json`.

## Ticket management

The preferred ticket system is [git-erg](https://github.com/MinhHaDuong/git-erg), an offline `tickets/` directory that lives inside each project's git repo. Install it per-project following its README. When git-erg is available, use it. Fall back to GitHub issues or any other forge when needed (e.g., for cross-team coordination).

### Optional: daily auto-update via systemd

To keep the harness up to date without a network hit on every session start:

```bash
# Create the service and timer
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/claude-harness-pull.service << 'EOF'
[Unit]
Description=Pull ImperialDragonHarness updates

[Service]
Type=oneshot
ExecStart=/usr/bin/git -C %h/.claude pull --ff-only --quiet
EOF

cat > ~/.config/systemd/user/claude-harness-pull.timer << 'EOF'
[Unit]
Description=Daily pull of ImperialDragonHarness

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start
systemctl --user daemon-reload
systemctl --user enable --now claude-harness-pull.timer
```

## Why not a plugin?

Because it's **my** harness. IDH is my personal Claude config, cloned to `~/.claude` on every machine I use. The plugin system exists for shareable, redistributable tooling — that's not this. Fork the repo if you want your own.
