# Review 3: Imperial Dragon Harness vs. 5 Levels of Harnessing

**Date:** 2026-04-04
**Reviewer:** Opus agent (level-by-level audit)

---

## Level-by-Level Audit

### Level 1: Raw Prompting

**Rating: Complete** (transcended)

The harness is well past raw prompting. Every file contains structured instructions, not ad-hoc prompts.

---

### Level 2: CLAUDE.md

**Rating: Complete**

| Evidence | Notes |
|----------|-------|
| Three rules files totaling ~88 lines | Well under 200-line threshold |
| `coding.md` (43 lines): Python style, testing, build | Tightly scoped, actionable |
| `git.md` (8 lines): branch discipline, commit messages | High-signal density |
| `workflow.md` (37 lines): session protocol, escalation | Dense decision table |
| `effortLevel: max` in settings | Config-level directive |

**Gaps:** No per-project CLAUDE.md differentiation — rules are all global (user-level). The split-rules approach is arguably better organized than a monolithic file.

---

### Level 3: Skills

**Rating: Complete**

| Evidence | Count |
|----------|-------|
| Custom skills in `~/.claude/skills/` | 8 skill files |
| GSD commands in `~/.claude/commands/gsd/` | 25+ command files |
| Skills use YAML frontmatter | `name`, `description`, `user-invocable`, `context` |
| `review-pr` uses `context: fork` for parallel agents | Multi-perspective review |
| `autonomous` manages parallel implementations | Up to 3 parallel, max 4 worktrees |

**Notable skills:** `start-ticket` (TDD workflow), `review-pr` (5 perspectives), `end-session` (9-step wrap-up), `memory` (TTLs, staleness, caps).

**Gaps:** No coding-pattern skills (e.g., "add module", "refactor"). Skills are workflow-oriented rather than coding-oriented.

---

### Level 4: Hooks

**Rating: Partial**

| Hook | Type | Status |
|------|------|--------|
| `on-start.sh` | SessionStart | Complete — auto-update, env, git identity, STATE.md |
| `block-pr-merge-in-worktree.sh` | PreToolUse | Complete — blocks `gh pr merge` in worktrees |
| PostToolUse (lint/format) | — | **Missing** |
| Stop (test enforcement) | — | **Missing** |
| PostToolUse (commit message validation) | — | **Missing** |
| Notification hooks | — | **Missing** |

The framework's key Level 4 criterion: *"you stop telling the agent to validate and start building infrastructure that validates for it."* Currently validation is told (via skills/rules), not built into infrastructure.

**Recommendation:** Add:
1. PostToolUse on Edit/Write → `ruff check --fix` on changed file
2. Stop hook → `make check-fast` before task completion
3. PostToolUse on `git commit` → verify "why not what" message convention

---

### Level 5: Orchestration

**Rating: Partial**

| Feature | Status |
|---------|--------|
| Worktree isolation | Complete — every conversation gets own worktree |
| Parallel agents | Partial — `review-pr` and `autonomous` use them |
| Cross-session state | Complete — STATE.md + MEMORY.md |
| Session chaining | Partial — `end-session` → `autonomous` handoff |
| Coordination layer (file conflicts) | **Missing** |
| Fleet management (multi-session orchestrator) | **Missing** |
| Merge conflict detection | **Missing** |
| Campaign tracking | **Missing** |

**Recommendation:** Add pre-merge conflict check (hook on `gh pr create` that runs `git merge --no-commit --no-ff main`). Consider campaign file tracking which files/modules are claimed by active worktrees.

---

## Summary

### Current Level Assessment

| Level | Rating | Status |
|-------|--------|--------|
| 1. Raw Prompting | Complete | Transcended |
| 2. CLAUDE.md | Complete | Via split rules files |
| 3. Skills | Complete | Strong, diverse library |
| 4. Hooks | **Partial** | SessionStart excellent; missing PostToolUse/Stop |
| 5. Orchestration | **Partial** | Worktrees + parallel agents; missing fleet coordination |

**The harness is solidly at Level 3 with significant Level 4 and 5 infrastructure in place.** The gap to fully achieving Level 4 is small and concrete. Level 5 is partially implemented but lacks fleet coordination.

### Top 3 Actions to Reach Level 4

1. **PostToolUse hook for file edits** → run linter on changed file, return errors to agent
2. **Stop hook** → run `make check-fast` before task completion (advisory → enforced)
3. **Pre-PR conflict check** → verify branch merges cleanly with main

### Strengths
- Session lifecycle fully automated (`on-start.sh` → skills → `end-session` → `autonomous`)
- Skill library exceptionally well-designed (proportional depth, multi-perspective, anti-patterns)
- Memory management disciplined (TTLs, staleness, caps, cross-referencing)
- Defensive hooks prevent known footguns
- Harness self-updates daily
