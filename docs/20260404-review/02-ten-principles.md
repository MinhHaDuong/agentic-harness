# Review 2: Imperial Dragon Harness vs. Forsythe's 10 Principles

**Date:** 2026-04-04
**Reviewer:** Opus agent (principle-by-principle audit)

---

## Principle-by-Principle Audit

### Principle 1: The Hardening Principle
*Every fuzzy LLM step that must behave identically every time must eventually be replaced by a deterministic tool.*

**Rating: Partial**

| Evidence | Gaps |
|----------|------|
| SessionStart hook hardcodes env setup, git identity, STATE.md injection | Worktree lifecycle is LLM-driven (could skip `EnterWorktree`) |
| PreToolUse hook deterministically blocks `gh pr merge` in worktrees | Phase announcement system is rules-only, no enforcement |
| Daily auto-pull is hardened cron-like mechanism | No PostToolUse hooks for linting/type-checking |

**Recommendation:** Add PostToolUse hook on file writes for linting. Consider PreToolUse hook blocking Bash/Edit until worktree is active.

---

### Principle 2: The Context Hygiene Principle
*Context is your scarcest resource. Treat it like memory in an embedded system.*

**Rating: Strong**

| Evidence | Gaps |
|----------|------|
| Rules total ~87 lines (coding 43, git 8, workflow 34) | `settings.local.json` is 132 lines of accumulated permissions |
| Tables and bullets, not prose | |
| STATE.md injected at beginning (positional advantage) | |
| `effortLevel: max` avoids verbose prompt instructions | |

**Recommendation:** Periodically prune `settings.local.json`.

---

### Principle 3: The Living Documentation Principle
*Documentation is context. Stale documentation is poisoned context.*

**Rating: Partial**

| Evidence | Gaps |
|----------|------|
| Harness auto-updates daily from remote | No automated freshness check for rule files |
| `git.md`: "Top-level files reflect *now*" | No timestamp/version markers in rules |
| STATE.md injected every session | `docs/` references have no freshness mechanism |

**Recommendation:** Add `last-reviewed` date header to each rules file. Consider periodic reminder for stale rules.

---

### Principle 4: The Disposable Blueprint Principle
*Never implement without a saved, versioned plan artifact.*

**Rating: Partial**

| Evidence | Gaps |
|----------|------|
| Workflow phases (Imagine/Plan/Execute/Verify) | No explicit plan artifact requirement (e.g., PLAN.md) |
| Git discipline supports disposable branches | No template or convention for plan documents |
| Worktree model: "all worktrees are throwaway" | Plan phase has no concrete deliverable |

**Recommendation:** Add to `workflow.md`: "The Plan phase produces a `PLAN.md` in the branch root before any code changes."

---

### Principle 5: The Institutional Memory Principle
*When an agent makes a mistake, codify it forever.*

**Rating: Strong**

| Evidence | Gaps |
|----------|------|
| `coding.md` built from always/never rules with reasons | No single canonical always/never list |
| Testing constraints learned from experience (source inspection vs. subprocess) | Constraints distributed across files |
| Escalation protocol: "Save feedback memory at each escalation" | |
| MEMORY.md provides persistent cross-session memory | |

**Recommendation:** Consider dedicated section for critical always/never rules as harness grows.

---

### Principle 6: The Specialized Review Principle
*A generalist reviewer trends toward the median. Specialists find what generalists can't.*

**Rating: Weak**

| Evidence | Gaps |
|----------|------|
| Escalation protocol mentions "parallel expert agents" | No defined specialist personas |
| No flattery anywhere in rules | No review workflow or checklist |
| | No mechanism to invoke specialist review agents |

**Recommendation:** Create specialist review personas in `skills/` (security, performance, API design), each under 50 tokens.

---

### Principle 7: The Observability Imperative
*If you can't see inside your pipeline, you're trusting it on faith.*

**Rating: Weak**

| Evidence | Gaps |
|----------|------|
| `on-start.sh` prints "Agent identity configured." | No structured logging of agent actions |
| Git history as implicit audit trail | No session summary at session end |
| Block-merge hook prints diagnostic message | No cost/token tracking |

**Recommendation:** Add Stop hook logging session summary (files changed, commits, tools invoked) to structured log.

---

### Principle 8: The Strategic Human Gate Principle
*Rubber-stamp approval is the single most common quality failure.*

**Rating: Strong**

| Evidence | Gaps |
|----------|------|
| Worktree + PR model creates natural human gate | Gates are somewhat implicit |
| `block-pr-merge-in-worktree.sh` prevents autonomous merging | No explicit "must get approval before X" list |
| Escalation protocol: "Stop -- ask the author" as final step | |
| Permission allowlist constrains agent capabilities | |

**Recommendation:** Add explicit list of 2-3 mandatory human gates to `workflow.md`.

---

### Principle 9: The Token Economy Principle
*Tokens are money. Most people are burning it.*

**Rating: Partial**

| Evidence | Gaps |
|----------|------|
| Single-agent default; multi-agent only at escalation step 3 | No token budget awareness or cost tracking |
| Lean rules (~87 lines) | No measurement of single-agent threshold |
| No flattery or bloated personas | `effortLevel: max` may be token-expensive |

**Recommendation:** Make `effortLevel` task-dependent rather than globally `max`.

---

### Principle 10: The Toolkit Principle
*Knowledge without automation decays. Encode your principles into tools.*

**Rating: Partial**

| Evidence | Gaps |
|----------|------|
| The harness IS a toolkit (settings + hooks + rules) | Only 2 hooks exist |
| Auto-update mechanism keeps toolkit current | Many rules are "soft" (LLM compliance, not tooling) |
| SessionStart automates manual setup | No PostToolUse for quality checks |
| PR-merge block encodes learned lesson | No skills directory for reusable procedures |

**Recommendation:** Add PostToolUse hooks for highest-value checks. Add PreToolUse on `git commit` to verify agent is on a branch.

---

## Summary

### Overall Score: 8/10 with Strong or Partial

| Principle | Rating |
|-----------|--------|
| 1. Hardening | Partial |
| 2. Context Hygiene | **Strong** |
| 3. Living Documentation | Partial |
| 4. Disposable Blueprint | Partial |
| 5. Institutional Memory | **Strong** |
| 6. Specialized Review | Weak |
| 7. Observability | Weak |
| 8. Strategic Human Gate | **Strong** |
| 9. Token Economy | Partial |
| 10. Toolkit | Partial |

**Strong: 3 | Partial: 5 | Weak: 2 | Missing: 0**

### Top 3 Priority Improvements
1. **PostToolUse hooks for automated quality checks** (hits Principles 1, 7, 10)
2. **Specialist review personas** (Principle 6 — biggest gap)
3. **Session-end observability** (Principle 7 — structured session summaries)

### Exceptional Strengths
- Context discipline (~87 lines, no flattery, dense tabular formatting)
- Worktree isolation model (prevents multi-session interference)
- PR-merge block hook (textbook hardening of a known failure mode)
