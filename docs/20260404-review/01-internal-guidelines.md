# Review 1: Imperial Dragon Harness vs. Internal Guidelines

**Date:** 2026-04-04
**Reviewer:** Opus agent (internal references audit)

---

## 1. Compliance Summary

| Area | Rating | Notes |
|------|--------|-------|
| **Session startup / context loading** | GREEN | Well-designed SessionStart hook with env persistence, git identity, STATE.md output |
| **Git workflow discipline** | GREEN | Strong branching rules, worktree isolation, PR enforcement |
| **Protection hooks** | YELLOW | One good PreToolUse guard (PR merge blocker), but several recommended protections missing |
| **Coding standards (rules)** | GREEN | Concise, project-specific, actionable Python/testing/build rules |
| **CLAUDE.md / project docs** | RED | No CLAUDE.md exists at all |
| **PostToolUse hooks (formatting/linting)** | RED | None defined despite Python/ruff being a key tool |
| **Notification hooks** | RED | None defined |
| **Skills** | RED | No custom skills defined in harness repo |
| **Agents (subagents)** | RED | No custom agents defined |
| **MCP servers** | YELLOW | No `.mcp.json` found; unclear if configured elsewhere |
| **Permissions hygiene** | YELLOW | `settings.local.json` has grown organically with one-off entries |
| **Secret safety** | YELLOW | `.env` contains a plaintext API key; no Write/Edit guard for `.env` files |

---

## 2. Strengths

**S1. SessionStart hook is well-architected** (`hooks/on-start.sh`)
- Daily auto-pull of the harness repo (idempotent stamp file).
- Two-tier `.env` persistence (user-level then project-level) via `CLAUDE_ENV_FILE`, matching the context-loading pattern in `plugin-dev/hook-development/references/patterns.md` (Pattern 3).
- Git identity and hooks-path setup are conditional and safe.
- Outputs `STATE.md` at end, giving Claude immediate project context.

**S2. Worktree-based isolation** (`rules/workflow.md`)
- Every conversation gets its own worktree with a naming convention tied to task type. Sophisticated pattern not present in any reference but solves real concurrency problems.

**S3. PR merge blocker is textbook PreToolUse guard** (`hooks/block-pr-merge-in-worktree.sh`)
- Correctly consumes stdin, checks worktree condition, exits with code 2 to deny, provides actionable workaround. Aligns with `plugin-dev/hook-development/references/patterns.md` (Pattern 1).

**S4. Rules files are concise and project-specific**
- `coding.md`: Concrete Python style, testing markers, build rules. No generic filler.
- `git.md`: Six lines of high-signal discipline.
- `workflow.md`: Decision table is dense and scannable.

**S5. Separation of tracked vs. local settings**
- `settings.json` (tracked) holds hooks and global config.
- `settings.local.json` (gitignored) holds per-machine permissions.

---

## 3. Gaps

| ID | Gap | Reference | Impact |
|----|-----|-----------|--------|
| G1 | No CLAUDE.md | `claude-md-management` quality criteria (20pts for Commands, 20pts for Architecture) | Each session rediscovers project layout |
| G2 | No PostToolUse hooks for formatting/linting | `hooks-patterns.md` recommends PostToolUse on Edit/Write for Ruff | Formatting drift between edits |
| G3 | No Stop hook for test/build enforcement | `patterns.md` (Pattern 2: Test Enforcement, Pattern 6: Build Verification) | Sessions can end without running tests |
| G4 | No Notification hooks | `hooks-patterns.md` recommends for `permission_prompt` and `idle_prompt` | Missed permission prompts when multitasking |
| G5 | No custom skills in harness repo | `skills-reference.md` outlines project skills (test generators, PR checklists) | Repeatable workflows require re-explanation |
| G6 | No custom agents/subagents | `subagent-templates.md` recommends code-reviewer, security-reviewer agents | No parallel expert fan-out |
| G7 | No `.mcp.json` for MCP servers | `mcp-servers.md` recommends GitHub MCP | Relies on `gh` CLI only |
| G8 | No sensitive-file Write/Edit protection | `hooks-patterns.md` (Block Sensitive File Edits) | Claude can write secrets to tracked files |

---

## 4. Violations

| ID | Violation | Reference | Severity |
|----|-----------|-----------|----------|
| V1 | Plaintext API key in `.env` without Write protection | `hooks-patterns.md` (Block Sensitive File Edits) | Medium |
| V2 | `settings.local.json` bloated with one-off permissions | `hooks-patterns.md` / `advanced.md` (configuration-driven approach) | Low |
| V3 | `skipDangerousModePermissionPrompt: true` without compensating guards | `hooks-patterns.md` (Pattern 7), `advanced.md` (Security Patterns) | Medium |
| V4 | `ExitWorktree` referenced but not automated | `advanced.md` (Cross-Event Workflows) | Low |

---

## 5. Recommendations (Prioritized)

### High Priority
1. **PreToolUse hook to block writes to sensitive files** — addresses V1, G8
2. **PreToolUse guard for destructive Bash commands** — addresses V3
3. **Create CLAUDE.md for harness repo** — addresses G1

### Medium Priority
4. **PostToolUse hook for Ruff formatting** on `Write|Edit` for `*.py` — addresses G2
5. **Stop hook for test enforcement** — addresses G3
6. **Notification hooks** for `permission_prompt` and `idle_prompt` — addresses G4
7. **Clean up `settings.local.json`** — addresses V2

### Lower Priority
8. **Create custom skills** (e.g., `/pr-check`) — addresses G5
9. **Create code-reviewer subagent** — addresses G6
10. **Add `.mcp.json` for GitHub MCP** — addresses G7
11. **Add worktree cleanup to session lifecycle** — addresses V4
