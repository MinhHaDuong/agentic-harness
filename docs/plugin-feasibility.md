# Plugin Architecture Feasibility: Imperial Dragon Harness

## Verdict: Yes, fully

The harness maps cleanly onto the official Claude Code plugin system. Every
component has a direct equivalent — including rules, which become companion
reference files inside an auto-invoked skill.

## Official plugin spec (April 2026)

Source: [code.claude.com/docs/en/plugins-reference](https://code.claude.com/docs/en/plugins-reference)

Claude Code ships a built-in plugin system with:
- CLI: `claude plugin install|uninstall|enable|disable|update`
- In-session: `/plugin` command, `/reload-plugins`
- Loading: `claude --plugin-dir ./path` for development
- Distribution: marketplace repos, official Anthropic marketplace
- Namespaced skills: `/idh:review-pr`

## Component mapping

| Harness component | Plugin equivalent | Notes |
|---|---|---|
| `skills/*/SKILL.md` | `skills/*/SKILL.md` | Identical format. Namespaced as `/idh:skill-name` |
| `hooks/*.sh` | `scripts/*.sh` + `hooks/hooks.json` | Hooks declared in JSON, scripts use `${CLAUDE_PLUGIN_ROOT}` |
| `rules/*.md` | `skills/harness-rules/*.md` | Rules as skill companion files (auto-invoked) |
| `commands/*.md` | `commands/*.md` | Identical. Legacy but supported |
| `commands/gsd/*.md` | `commands/gsd/*.md` | Same |
| `bin/*` | `bin/*` | Official: added to Bash PATH when plugin enabled |
| `settings.json` | `settings.json` at plugin root | Only `agent` key currently supported by plugins |
| `docs/*` | Stays as documentation, not loaded | Same |

## Plugin directory layout

```
imperial-dragon/
├── .claude-plugin/
│   └── plugin.json           # name, version, description, author
├── skills/                   # 9 skills, identical SKILL.md format
│   ├── harness-rules/        # rules as companion files (auto-invoked)
│   │   ├── SKILL.md
│   │   ├── workflow.md
│   │   ├── git.md
│   │   ├── coding.md
│   │   └── state.md
│   ├── new-ticket/SKILL.md
│   ├── start-ticket/SKILL.md
│   ├── review-pr/SKILL.md
│   ├── review-pr-prose/SKILL.md
│   ├── celebrate/
│   │   ├── SKILL.md
│   │   └── log-celebration   # companion script
│   ├── end-session/
│   │   ├── SKILL.md
│   │   └── log-agent-metrics
│   ├── memory/SKILL.md
│   └── autonomous/SKILL.md
├── commands/                 # guidance documents
│   ├── choose-journal.md
│   └── gsd/                  # 33 research workflow commands
├── hooks/
│   └── hooks.json            # declares all hook events + matchers
├── scripts/                  # hook implementations
│   ├── on-start.sh
│   ├── guard-destructive-bash.sh
│   ├── guard-commit-on-main.sh
│   ├── block-pr-merge-in-worktree.sh
│   ├── lint-on-edit.sh
│   ├── check-tests-on-stop.sh
│   └── warn-stale-rules.sh
├── bin/                      # utilities on PATH
│   ├── usage-report
│   ├── snapshot
│   └── install-cron
└── docs/                     # not loaded by plugin system
```

## Rules as skill reference material

The official plugin system has no `rules/` directory. But skills support
companion files alongside `SKILL.md` — Claude reads them when the skill
is invoked.

### Solution: `skills/harness-rules/`

```
skills/harness-rules/
├── SKILL.md          # auto-invoked, not user-invocable
├── workflow.md       # session start, escalation, worktree isolation
├── git.md            # branch discipline, commit standards
├── coding.md         # Python 3.10+, testing, Make patterns
└── state.md          # STATE.md format specification
```

The skill uses `disable-model-invocation: false` + `user-invocable: false`,
so Claude auto-invokes it at session start when it recognizes the project
context. The SKILL.md instructs Claude to read and follow all companion files.

### Trade-offs vs standalone rules

| | `~/.claude/rules/` | `skills/harness-rules/` |
|---|---|---|
| **Loaded** | Always, every session | When Claude judges it relevant |
| **Deterministic** | Yes — rules always fire | Probabilistic — skill may not trigger |
| **Bundled in plugin** | No | Yes |
| **Path-scoped** | Yes (`paths:` frontmatter) | No (skill-level only) |

The key difference: rules are **deterministic** (always loaded), skills are
**probabilistic** (Claude decides). For a plugin meant for distribution,
probabilistic loading is acceptable — the skill description is specific
enough that Claude will invoke it reliably for any Imperial Dragon project.

For personal use where deterministic loading is required, keep standalone
rules in `~/.claude/rules/` alongside the plugin. Both approaches can
coexist.

## Migration effort

| Task | Size | Notes |
|---|---|---|
| Create `.claude-plugin/plugin.json` | Trivial | Just metadata |
| Move `hooks/*.sh` to `scripts/` | Trivial | Rename directory |
| Create `hooks/hooks.json` | Small | Translate settings.json hooks format |
| Update hook paths to use `${CLAUDE_PLUGIN_ROOT}` | Small | Search-replace |
| Test with `claude --plugin-dir` | Small | Verify all components load |
| Namespace skill invocations in docs | Small | `/review-pr` becomes `/idh:review-pr` |
| Package rules as skill companion files | Small | Create `skills/harness-rules/SKILL.md` + copy 4 rule files |

**Total**: ~2 hours of mechanical work. No design changes needed.

## What we gain

- **`claude plugin install`** — standard install, no custom scripts
- **`/reload-plugins`** — hot-reload during development
- **Marketplace distribution** — share via Git repo or official marketplace
- **Namespacing** — no skill name collisions with other plugins
- **`${CLAUDE_PLUGIN_ROOT}`** — portable paths, no hardcoded `$HOME/.claude`
- **Enable/disable** — toggle without uninstalling
- **Version updates** — `claude plugin update` with semver tracking

## What we lose

Nothing functional. The custom `bin/plugin-*` scripts we prototyped are
strictly inferior to the built-in CLI.

The one nuance: rules loaded via skill are **probabilistic** (Claude
decides when to invoke) rather than **deterministic** (always loaded).
In practice this is fine for distribution. For personal use where
guaranteed loading matters, keep standalone `~/.claude/rules/` alongside
the plugin — both coexist cleanly.

## Decision

Restructure the harness as an official Claude Code plugin. Keep rules in
`~/.claude/rules/` as a separate concern. No custom plugin management
tooling needed — the built-in system covers all use cases.
