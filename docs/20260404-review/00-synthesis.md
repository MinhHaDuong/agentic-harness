# Imperial Dragon Harness — Review Synthesis

**Date:** 2026-04-04
**Reviews synthesized:** 5 (internal guidelines, 10 principles, 5 levels, PR review, deep research)

---

## Overall Assessment

The Imperial Dragon Harness is **well above average** — concise (87 lines of rules), architecturally sound (worktree isolation, auto-updating, deterministic hooks), and aligned with peer-reviewed research on LLM assistant configuration. It avoids the most damaging anti-patterns (flattery, over-specification, agent proliferation) while implementing the highest-leverage practices (verification infrastructure, hooks, isolation, brevity).

**Current maturity: Level 3 (Skills) fully achieved, Level 4 (Hooks) partially achieved.**

---

## Convergent Findings

These issues surfaced across 3+ reviews — high confidence they matter:

### Critical (all 5 reviews flagged)

| # | Finding | Reviews |
|---|---------|---------|
| **C1** | **No PostToolUse hooks** — linting/formatting after edits is advisory, not enforced. This is the single highest-leverage gap. | Internal, 10 Principles (1,7,10), 5 Levels (4), PR Review |
| **C2** | **`skipDangerousModePermissionPrompt: true` without compensating guards** — only 1 PreToolUse hook exists (PR merge block). No guard on destructive Bash commands despite broad `sudo` permissions. | Internal, PR Review (Security), 10 Principles (8) |
| **C3** | **`settings.local.json` is bloated** — 140 lines of accumulated one-off permissions including `sudo tee:*`, `sudo cp:*`. Not a curated policy. | Internal, PR Review (Security, Scope), 10 Principles (2) |

### Major (3-4 reviews flagged)

| # | Finding | Reviews |
|---|---------|---------|
| **M1** | **No Stop hook for test enforcement** — "run tests" is a skill instruction, not infrastructure. Level 4 criterion: "infrastructure validates for you." | Internal, 5 Levels, 10 Principles (1,10) |
| **M2** | **No observability / session logging** — no structured record of what happened during a session beyond git commits. | 10 Principles (7), PR Review, Deep Research |
| **M3** | **`on-start.sh` early exit bug** — when `CLAUDE_PROJECT_DIR` is unset, user-level `.env` loading is skipped (functional bug). | PR Review (Correctness) |
| **M4** | **Stated rules not enforced** — "main is read-only" and "every conversation in worktree" are rules only, not hooks. Gap between documentation and enforcement erodes trust. | PR Review (Consistency), 10 Principles (1,10), 5 Levels (4) |
| **M5** | **`effortLevel: max` globally** — Anthropic warns Opus 4.6 does excessive exploration at max. Should be task-dependent. | Deep Research, 10 Principles (9) |
| **M6** | **No specialist review personas** — biggest gap against Forsythe Principle 6. No review workflow beyond PRs. | 10 Principles (6), Internal (G6) |

### Minor (2 reviews flagged)

| # | Finding | Reviews |
|---|---------|---------|
| **m1** | No CLAUDE.md for harness repo itself | Internal, 5 Levels |
| **m2** | `docs/` mixes harness docs with unrelated research | PR Review (Scope, Docs) |
| **m3** | No compaction survival instruction | Deep Research |
| **m4** | No living documentation freshness check | 10 Principles (3), Deep Research |
| **m5** | Auto-pull from remote has no signature verification | PR Review (Security) |

---

## Strengths (unanimous across reviews)

1. **Context discipline is outstanding** — 87 lines, no flattery, dense tabular formatting. Textbook Principle 2.
2. **Worktree isolation model is architecturally sound** — prevents multi-session interference, enables attributable testing.
3. **PR-merge block hook is exemplary hardening** — deterministic guard with diagnostic message and workaround.
4. **Session lifecycle is fully automated** — `on-start.sh` → skills → `end-session` → `autonomous` chain.
5. **Memory management is disciplined** — TTLs, staleness criteria, list caps, cross-referencing.

---

## Prioritized Action Plan

### Tier 1: Fix bugs and close security gaps (do now)

| Ticket | Action | Addresses |
|--------|--------|-----------|
| **T1** | Fix `on-start.sh` early exit — move user-level `.env` loading before project-dir check | M3 |
| **T2** | Add PreToolUse hook for destructive Bash commands (`rm -rf`, `git reset --hard`, `sudo`) | C2 |
| **T3** | Audit and prune `settings.local.json` — remove one-offs, narrow `sudo` grants, document policy | C3 |

### Tier 2: Reach Level 4 (next sprint)

| Ticket | Action | Addresses |
|--------|--------|-----------|
| **T4** | Add PostToolUse hook on Write/Edit → run `ruff check --fix` on changed `.py` files | C1 |
| **T5** | Add Stop hook → run `make check-fast`, block if tests fail | M1 |
| **T6** | Add PreToolUse hook on `git commit` → verify not on main branch | M4 |
| **T7** | Reduce `effortLevel` from `max` to `high`; document when to override | M5 |

### Tier 3: Strengthen review and observability (following sprint)

| Ticket | Action | Addresses |
|--------|--------|-----------|
| **T8** | Create 2-3 specialist review personas (<50 tokens each) in skills | M6 |
| **T9** | Add session-end logging (files changed, commits, phase, escalations) | M2 |
| **T10** | Add compaction survival instruction to rules | m3 |
| **T11** | Add `last-reviewed` dates to rule files + staleness warning | m4 |

### Tier 4: Polish (backlog)

| Ticket | Action | Addresses |
|--------|--------|-----------|
| **T12** | Create CLAUDE.md for harness repo | m1 |
| **T13** | Clean up `docs/` — move unrelated files, add index | m2 |
| **T14** | Add Notification hooks for `permission_prompt` and `idle_prompt` | Internal G4 |
| **T15** | Add pre-PR conflict check hook | 5 Levels (5) |

---

## Evidence Base

This synthesis is grounded in:
- **8 peer-reviewed papers** (Liu et al. 2024, MAST 2025, DeepMind 2025, PRISM 2026, MetaGPT 2024, ETH Zurich 2026, CHI 2023, Mind Your Tone 2025)
- **3 official Anthropic documents** (best practices, prompt engineering, internal usage)
- **4 industry analyses** (Forsythe 10 principles, HumanLayer, community reports)
- **12 internal reference files** from Claude Code plugins
