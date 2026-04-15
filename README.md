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
├── .claude-plugin/
│   └── plugin.json         # Plugin manifest (kept for future use)
├── skills/                 # Slash commands: /celebrate, /review-pr, etc.
│   ├── harness-rules/      # Auto-invoked rules (companion .md files)
│   │   ├── SKILL.md
│   │   ├── workflow.md         # Session start, escalation, worktree
│   │   ├── git.md              # Branch, commit, PR discipline
│   │   ├── coding.md           # Python style, testing, Make
│   │   └── state.md            # STATE.md format spec
│   ├── new-ticket/         # GitHub issue template
│   ├── start-ticket/       # Begin work on issue (TDD)
│   ├── review-pr/          # Multi-agent code review
│   ├── review-pr-prose/    # Peer review panel for prose
│   ├── celebrate/          # Post-task wrap-up
│   ├── end-session/        # Day wrap-up
│   ├── memory/             # Persistent memory management
│   ├── orchestrator/       # Batch across multiple tickets
│   └── autonomous/         # Unsupervised exploration session
├── hooks/
│   └── hooks.json          # Plugin-mode hooks (mirrors settings.json)
├── scripts/                # Hook implementations
│   ├── on-start.sh             # Session start: env loading, worktree gate
│   ├── guard-destructive-bash.sh
│   ├── guard-commit-on-main.sh
│   ├── block-pr-merge-in-worktree.sh
│   └── lint-on-edit.sh
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

3. Add the shell alias to your `~/.bashrc` (or `~/.zshrc`):
   ```bash
   alias claude='claude --dangerously-skip-permissions'
   ```
   The harness enforces worktree isolation via a SessionStart hook, so every new chat automatically enters its own worktree.

Skills are available as `/celebrate`, `/review-pr`, etc. Hooks fire automatically via `settings.json`.

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

Claude Code supports a plugin system (`--plugin-dir`, `.claude-plugin/`, namespaced skills). This repo has plugin scaffolding but is not used as a plugin. Instead, it *is* the `~/.claude` directory.

Reasons:

- **Hooks and settings live in `~/.claude/settings.json`**. A plugin can ship `hooks.json` and its own settings, but user-level hooks and `env` vars must be in the user config directory. Running as `~/.claude` means one source of truth.
- **Memory and state are user-level**. The `projects/` memory directory and `.env` file belong in `~/.claude`. A plugin would need symlinks or copies.
- **No namespace friction**. As `~/.claude`, skills register as `/celebrate`, not `/idh:celebrate`. Shorter to type, easier to remember.
- **Simpler mental model**. "The harness is my Claude config" vs. "the harness is a plugin loaded into my Claude config."

The plugin manifest (`.claude-plugin/plugin.json`) is kept for potential future use — loading the harness on machines where `~/.claude` already exists for other purposes.
