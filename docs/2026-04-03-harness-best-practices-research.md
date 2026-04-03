# Claude Code Harness Best Practices: Evidence-Based Research Report

**Date:** 2026-04-03
**Scope:** Measurably proven practices for designing Claude Code harnesses (AI coding assistant configuration systems)

---

## 1. Executive Summary

The empirical research on LLM coding assistant configuration converges on a counterintuitive conclusion: less is more. Shorter instruction files outperform longer ones (ETH Zurich: LLM-generated context files *reduce* success rates by 3% while costing 20%+ more tokens). Fewer agents outperform many (DeepMind: 5 agents cost 7x tokens but yield only 3.1x output; at 7+ agents, performance *degrades*). Terse persona descriptions outperform elaborate ones (PRISM: personas under 50 tokens outperform 200+ token descriptions). Critical information must be positioned at the beginning or end of context, not the middle (Liu et al.: 30%+ accuracy drop for mid-context placement). The highest-leverage intervention is not prompt engineering but *verification infrastructure* -- giving the agent tests, linters, and screenshots so it can check its own work. The Imperial Dragon Harness is well-aligned with this research: it is concise (87 lines across three rule files), uses hooks for deterministic enforcement, and avoids flattery and over-specification. Its main improvement opportunities are minor.

---

## 2. Proven Practices

### 2.1 Context Hygiene: Keep Instructions Minimal

**Practice:** Keep CLAUDE.md/rules files as short as possible. Only include instructions that would cause mistakes if omitted.

**Evidence:**
- **ETH Zurich (Feb 2026):** Tested 138 agentfiles across 4 coding agents (Claude, Codex, Qwen Code) on AGENTbench and SWE-bench Lite. LLM-generated context files *reduced* task success rate by 0.5-3% while increasing token consumption by 14-22%. Human-written files improved success by only ~4%, still at 14-22% higher token cost. [arxiv.org/html/2602.11988v1](https://arxiv.org/html/2602.11988v1)
- **HumanLayer analysis:** Frontier LLMs can follow ~150-200 instructions with reasonable consistency. Claude Code's own system prompt consumes ~50 of those slots. Every additional instruction competes for a finite instruction-following budget, with linear decay as instruction count rises. [humanlayer.dev/blog/writing-a-good-claude-md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- **Anthropic official docs:** "If your CLAUDE.md is too long, Claude ignores half of it because important rules get lost in the noise." Recommended: under 200 lines, ideally under 60. [code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)
- **Prompt bloat research (2025):** Reasoning performance degrades at ~3000 tokens, well below context window limits. Every extra 500 tokens adds ~25ms latency. [blog.promptlayer.com/disadvantage-of-long-prompt-for-llm/](https://blog.promptlayer.com/disadvantage-of-long-prompt-for-llm/)

**Measured impact:** ~4% improvement ceiling from human-written context files; 14-22% token overhead penalty; performance *decreases* with LLM-generated files.

### 2.2 Position Critical Information at Boundaries

**Practice:** Place the most important instructions at the beginning or end of context, never in the middle.

**Evidence:**
- **Liu et al. (TACL 2024), "Lost in the Middle":** With 20 input documents, accuracy on multi-document QA dropped by 30%+ when the relevant document was positioned in the middle (positions 5-15) vs. at position 1 or 20. GPT-3.5-Turbo's performance in the middle positions fell *below closed-book performance* (i.e., worse than having no context at all). U-shaped attention curve confirmed across multiple models. [aclanthology.org/2024.tacl-1.9/](https://aclanthology.org/2024.tacl-1.9/)
- **Anthropic official docs:** "Put longform data at the top... Queries at the end can improve response quality by up to 30% in tests." [platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices)

**Measured impact:** 30%+ accuracy differential between boundary vs. middle placement.

### 2.3 Verification is the Highest-Leverage Investment

**Practice:** Give the agent tests, linters, screenshots, or expected outputs so it can verify its own work.

**Evidence:**
- **Anthropic official docs:** "This is the single highest-leverage thing you can do." Stated as the #1 recommendation in their best practices guide. [code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)
- **MAST taxonomy (Cemri et al., 2025):** Task verification failures (FM-3.1 premature termination 6.2%, FM-3.2 no/incomplete verification 8.2%, FM-3.3 incorrect verification 9.1%) account for 23.5% of all multi-agent system failures. Human expert interventions adding verification improved success rates by +15.6%. [arxiv.org/abs/2503.13657](https://arxiv.org/abs/2503.13657)

**Measured impact:** +15.6% success rate from enhanced verification (MAST); qualitatively described as "single highest-leverage" by Anthropic.

### 2.4 Use Hooks for Deterministic Enforcement

**Practice:** Use hooks (not prompt instructions) for anything that must happen every time with zero exceptions.

**Evidence:**
- **Anthropic official docs:** "Unlike CLAUDE.md instructions which are advisory, hooks are deterministic and guarantee the action happens." [code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)
- **Forsythe Principle 1 (Hardening Principle):** "Every fuzzy LLM step that must behave identically every time must eventually be replaced by a deterministic tool." Supported by the observation that LLMs are probabilistic -- same input, different output. [jdforsythe.github.io/10-principles/overview/](https://jdforsythe.github.io/10-principles/overview/)

**Measured impact:** 100% reliability vs. probabilistic adherence (exact improvement depends on the instruction's compliance rate without hooks). *Note: specific quantified comparison not available in published research; the logic is sound but the exact magnitude is opinion-grade.*

### 2.5 Plan-Then-Code Workflows Reduce Errors

**Practice:** Separate planning from implementation. Create versioned plan artifacts before coding.

**Evidence:**
- **MetaGPT (Hong et al., ICLR 2024):** Teams using structured artifacts (PRDs, design docs, interface specs) before coding achieved 85.9% and 87.7% Pass@1 on HumanEval and MBPP respectively. The paper reports ~40% fewer errors with structured artifacts vs. free dialogue. [proceedings.iclr.cc/paper_files/paper/2024/file/6507b115562bb0a305f1958ccc87355a-Paper-Conference.pdf](https://proceedings.iclr.cc/paper_files/paper/2024/file/6507b115562bb0a305f1958ccc87355a-Paper-Conference.pdf)
- **Anthropic official docs:** Recommends a 4-phase workflow: Explore (Plan Mode) -> Plan -> Implement -> Commit. [code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)

**Measured impact:** ~40% error reduction from structured planning artifacts (MetaGPT).

### 2.6 Use Terse, Role-Based Personas (No Flattery)

**Practice:** Use brief professional role descriptions (under 50 tokens). Avoid flattery or elaborate persona backstories.

**Evidence:**
- **PRISM (2026):** Expert personas improve alignment-dependent tasks (writing +0.65, extraction +0.65, STEM +0.60, reasoning +0.40) but *damage* factual accuracy (MMLU: 68.0% with persona vs. 71.6% without, a 3.6pp drop). Longer persona prompts damage more. Coding performance specifically *decreased* by 0.65 points with expert personas. [arxiv.org/abs/2603.18507](https://arxiv.org/abs/2603.18507)
- **"Mind Your Tone" (2025):** Tested 250 prompts across 5 politeness levels. Rude prompts (80.8-84.8% accuracy) outperformed polite ones -- likely because directness reduces hedging. The measured gradient: Very Polite 80.8% < Polite < Neutral < Rude < Very Rude 84.8%. [arxiv.org/abs/2510.04950](https://arxiv.org/abs/2510.04950)

**Measured impact:** 3.6pp accuracy loss from expert personas on knowledge tasks; ~4pp accuracy range between politeness levels.

### 2.7 Worktree Isolation for Parallel Agent Sessions

**Practice:** Run each agent session in its own git worktree to prevent file-state interference.

**Evidence:**
- **Claude Code architecture (leaked source analysis, March 2026):** Internally uses three execution models for sub-agents: Fork, Teammate, and Worktree -- with Worktree providing the strongest isolation (own git worktree, isolated branch per agent). [venturebeat.com/technology/claude-codes-source-code-appears-to-have-leaked-heres-what-we-know](https://venturebeat.com/technology/claude-codes-source-code-appears-to-have-leaked-heres-what-we-know)
- **Community consensus (2025-2026):** Worktree isolation enables reliable test runs -- each agent's tests reflect only that agent's changes against a clean baseline. Without isolation, merged file states make test failures unattributable. [nrmitchi.com/2025/10/using-git-worktrees-for-multi-feature-development-with-ai-agents/](https://www.nrmitchi.com/2025/10/using-git-worktrees-for-multi-feature-development-with-ai-agents/)

**Measured impact:** Qualitative (prevents cross-contamination and enables attributable test results). *No controlled study with quantified improvement found; evidence is architectural/logical rather than experimental.*

### 2.8 Delegate Linting to Deterministic Tools

**Practice:** Never use prompt instructions for code style that a linter can enforce. Use hooks to run linters instead.

**Evidence:**
- **HumanLayer analysis:** "Never send an LLM to do a linter's job. LLMs are comparably expensive and incredibly slow compared to traditional linters and formatters." [humanlayer.dev/blog/writing-a-good-claude-md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- **Anthropic official docs:** Code style rules that differ from defaults should be included; standard conventions Claude already knows should be excluded. [code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)

**Measured impact:** Token savings (linting instructions consume context budget for zero benefit when a linter already enforces them). *Exact savings not quantified in published studies.*

### 2.9 Context-Efficient Session Management

**Practice:** One task per session, max ~20 iterations. Use /clear between unrelated tasks. Use subagents for investigation to preserve main context.

**Evidence:**
- **Anthropic official docs:** "After two failed corrections, /clear and write a better initial prompt." Subagents "explore in a separate context, keeping your main conversation clean for implementation." [code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)
- **Community-reported data (2026):** "One task, one session, max 20 iterations is the single biggest workflow change that reduces token waste." RTK hooks reported 68.9% efficiency and 64.9K tokens saved over two days. [richardporter.dev/blog/claude-code-token-management](https://richardporter.dev/blog/claude-code-token-management)

**Measured impact:** 64.9K tokens saved over 2 days with aggressive context management (community-reported, not peer-reviewed).

---

## 3. Anti-Patterns

### 3.1 Flattery and Elaborate Persona Descriptions

**Practice to avoid:** "You are the world's best programmer" or multi-paragraph persona backstories.

**Evidence:**
- **PRISM (2026):** Expert personas reduce MMLU accuracy by 3.6pp (71.6% -> 68.0%). Coding performance specifically dropped 0.65 points. Longer descriptions damage more. The mechanism: flattery activates motivational/marketing training data rather than technical expertise clusters. [arxiv.org/abs/2603.18507](https://arxiv.org/abs/2603.18507)

**Measured harm:** 3.6pp accuracy loss on knowledge retrieval; 0.65 point coding degradation.

### 3.2 Over-Specified System Prompts

**Practice to avoid:** Including 19+ requirements or instructions the model would follow anyway.

**Evidence:**
- **HumanLayer analysis:** Instruction-following quality degrades linearly with instruction count; ~150-200 instruction capacity for frontier models, ~50 already consumed by Claude Code's system prompt. [humanlayer.dev/blog/writing-a-good-claude-md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- **ETH Zurich (2026):** LLM-generated agentfiles that contained exhaustive instructions hurt performance by 0.5-3% while costing 14-22% more tokens. [arxiv.org/html/2602.11988v1](https://arxiv.org/html/2602.11988v1)

**Measured harm:** -0.5 to -3% success rate; +14-22% token cost.

### 3.3 Agent Proliferation

**Practice to avoid:** Spawning 5+ agents for tasks a single well-prompted agent could handle.

**Evidence:**
- **DeepMind/MIT "Towards a Science of Scaling Agent Systems" (Dec 2025):** 180 configurations tested across GPT, Gemini, Claude. Independent agents amplified errors 17.2x vs. single-agent baseline. Coordination overhead: independent 58%, centralized 285%, hybrid 515% token overhead. Mean improvement across domains: -3.5% (sigma=45.2%). The 45% threshold: if a single agent achieves >45% accuracy, adding more agents yields negative returns (beta=-0.408, p<0.001). Turn counts scale super-linearly with agent count (exponent 1.724, R^2=0.974). [arxiv.org/abs/2512.08296](https://arxiv.org/abs/2512.08296)

**Measured harm:** 17.2x error amplification (independent agents); negative mean improvement (-3.5%); 58-515% token overhead.

### 3.4 Rubber-Stamp Review Agents

**Practice to avoid:** Using LLM review agents without adversarial prompting.

**Evidence:**
- **MAST taxonomy (2025):** FM-3.1 (premature termination) was the most frequently observed quality failure. LLMs are sycophantic by default and trend toward agreement. Multi-agent systems showed 41-86.7% failure rates across 7 frameworks. [arxiv.org/abs/2503.13657](https://arxiv.org/abs/2503.13657)

**Measured harm:** Review agents approve flawed code at high rates without adversarial forcing. *Exact false-positive rate for review agents not quantified, but the underlying sycophancy mechanism is well-documented.*

### 3.5 LLM-Generated Configuration Files

**Practice to avoid:** Auto-generating CLAUDE.md or agentfiles with LLMs.

**Evidence:**
- **ETH Zurich (2026):** LLM-generated context files degraded performance in 5 out of 8 test settings, reducing success rates by up to 3% while increasing costs by 20%+. [the-decoder.com/context-files-for-coding-agents-often-dont-help-and-may-even-hurt-performance/](https://the-decoder.com/context-files-for-coding-agents-often-dont-help-and-may-even-hurt-performance/)

**Measured harm:** -0.5 to -3% success rate; +20% cost.

### 3.6 Stale Documentation in Context

**Practice to avoid:** Including outdated instructions that contradict current project state.

**Evidence:**
- **Forsythe Principle 3 (Living Documentation):** Documented a case where one stale line about preferring `Array<T>` over `T[]` triggered cascading ESLint violations. "When docs rot, the model's output rots with them." [jdforsythe.github.io/10-principles/overview/](https://jdforsythe.github.io/10-principles/overview/)

**Measured harm:** Anecdotal (cascading build failures from one stale instruction). *Systematic measurement not available.*

---

## 4. Harness Assessment: Imperial Dragon Harness

### 4.1 Strengths (well-aligned with research)

| Aspect | Assessment | Supporting Evidence |
|--------|-----------|-------------------|
| **Total size: 87 lines across 3 rule files** | Excellent. Well under the 200-line threshold, approaching HumanLayer's recommended ~60-line ideal. | ETH Zurich study; HumanLayer analysis |
| **No flattery or persona inflation** | Excellent. Rules are direct, professional, and imperative. No "you are the world's best" language. | PRISM research; "Mind Your Tone" study |
| **Deterministic hooks for critical behaviors** | Excellent. SessionStart hook handles env/identity setup deterministically. PreToolUse hook blocks `gh pr merge` in worktrees. | Anthropic best practices; Forsythe Principle 1 |
| **Worktree isolation mandated** | Excellent. Every conversation runs in its own worktree, with branches holding durable state. | Claude Code architecture; community consensus |
| **Clear verification workflow** | Good. `make check-fast` and `make check` provide tiered verification. Testing rules specify markers for unit/integration/slow tests. | Anthropic #1 recommendation; MAST findings |
| **Linting delegated to tools, not prompts** | Partially good. The rules mention `make check-fast` includes lint but do not include style instructions that overlap with linters. Some Python style rules (built-in generics, union syntax) *could* be enforced by a linter instead. | HumanLayer analysis |
| **Plan-then-code workflow implicit** | Good. The workflow.md phase table (Imagine -> Plan -> Execute -> Verify) aligns with MetaGPT findings on structured planning. | MetaGPT research |
| **Escalation protocol** | Good. Progressive escalation with a hard stop at 3 attempts prevents infinite loops. Matches MAST finding that step repetition (15.7%) is a top failure mode. | MAST taxonomy |
| **One change per commit** | Good discipline. Reduces context confusion and enables clean revert. | General software engineering best practice (not specifically measured for LLM agents) |

### 4.2 Potential Improvements

| Issue | Evidence Basis | Severity |
|-------|---------------|----------|
| **Python style rules that a linter could enforce** | Lines like "Built-in generics: `list[str]`..." and "`X \| Y` union syntax" could be enforced by `ruff` or `mypy` configuration instead of consuming instruction budget. ETH Zurich: every instruction adds 14-22% token overhead. | Low. These are ~4 lines and arguably serve as documentation for human readers too. Only worth moving to linter config if the harness is nearing capacity. |
| **No explicit instruction about information positioning** | Liu et al.'s 30%+ accuracy drop for mid-context placement is a well-measured effect. The harness does not instruct the agent on how to structure its own context when reading files or building prompts for subagents. | Low-Medium. Anthropic's built-in system prompt already places CLAUDE.md at the beginning. This matters more for custom agentic pipelines than for standard Claude Code usage. |
| **No explicit compaction survival instructions** | Anthropic recommends adding CLAUDE.md instructions like "When compacting, always preserve the full list of modified files and any test commands." The harness does not include compaction guidance. | Low. Relevant for long sessions. The worktree-per-session pattern naturally limits session length. |
| **settings.json has `"effortLevel": "max"`** | Anthropic's Claude 4.6 best practices note that Opus 4.6 "does significantly more upfront exploration than previous models, especially at higher effort settings" and may spawn excessive subagents. They recommend replacing blanket maximums with targeted instructions. | Medium. `max` effort may cause unnecessary exploration and token burn on simple tasks. Consider `high` as default with explicit escalation to `max` for complex tasks. |
| **No explicit subagent guidance** | Anthropic notes Opus 4.6 "has a strong predilection for subagents and may spawn them in situations where a simpler, direct approach would suffice." The harness does not constrain subagent usage. | Low-Medium. The worktree isolation pattern helps, but explicit guidance on when subagents are warranted (per Anthropic's recommendation) could reduce token waste. |
| **Workflow table loaded every session regardless of relevance** | The 5-row routing table in workflow.md is loaded in every session but only one row applies. HumanLayer notes Claude "actively ignores CLAUDE.md content deemed irrelevant to current tasks" but processing it still costs tokens. | Very Low. At 37 lines, workflow.md is already concise. The routing table is clear and fast to parse. |

### 4.3 Overall Assessment

The Imperial Dragon Harness scores **well above average** against the research evidence:

- **Context hygiene:** 87 lines total -- outstanding. Most community harnesses are 200-500+ lines.
- **Anti-pattern avoidance:** No flattery, no over-specification, no agent proliferation instructions.
- **Deterministic enforcement:** Hooks handle environment setup and safety gates.
- **Verification infrastructure:** Tiered test commands with clear markers.
- **Isolation:** Worktree-per-session is best practice.

The harness reflects disciplined engineering rather than vibes-based configuration. It avoids the most damaging anti-patterns (over-specification, flattery, auto-generation) while implementing the highest-leverage practices (verification, hooks, isolation, brevity).

---

## 5. Recommendations (Prioritized by Evidence Strength)

### High Priority (strong evidence, measurable impact)

1. **Consider reducing `effortLevel` from `max` to `high`** -- Anthropic's own documentation warns that `max` on Opus 4.6 causes excessive exploration and subagent spawning. The `high` setting still enables deep reasoning while reducing token waste on simple tasks. Reserve `max` for complex multi-file changes via explicit prompt override.

2. **Add compaction survival instruction** -- A single line in one of the rule files: "When compacting, preserve the list of modified files, test commands, and current implementation plan." This is a low-cost, evidence-supported guard against context loss during long sessions.

### Medium Priority (moderate evidence, logical benefit)

3. **Add subagent usage guidance** -- Per Anthropic's recommendation: "Use subagents when tasks can run in parallel or require isolated context. For single-file edits or simple tasks, work directly." Reduces unnecessary subagent spawning that Opus 4.6 is prone to.

4. **Move Python type syntax rules to ruff/mypy configuration** -- The `list[str]` vs `List[str]` and `X | Y` vs `Union[X, Y]` rules could be enforced by `ruff` rules (UP006, UP007) rather than consuming instruction-following budget. Keep the remaining Python rules (argparse, logging, no sys.path hacks) which are harder to lint.

### Low Priority (logical benefit, limited quantified evidence)

5. **Add adversarial review prompting guidance** -- When using subagents for code review, instruct them to "find at least 3 issues" rather than asking for general review. This counters the sycophancy bias documented in MAST (FM-3.1).

6. **Consider a living documentation check** -- The Forsythe Living Documentation Principle suggests automated freshness checks for instruction files. A simple hook that warns when rule files have not been reviewed in 30+ days could prevent stale-instruction cascades.

---

## 6. Sources

### Peer-Reviewed Research

- Liu, N.F., Lin, K., Hewitt, J., et al. (2024). "Lost in the Middle: How Language Models Use Long Contexts." *Transactions of the Association for Computational Linguistics*. [aclanthology.org/2024.tacl-1.9/](https://aclanthology.org/2024.tacl-1.9/)

- Cemri, M., Pan, M.Z., Yang, S., et al. (2025). "Why Do Multi-Agent LLM Systems Fail?" *NeurIPS 2025 Datasets and Benchmarks Track (Spotlight)*. [arxiv.org/abs/2503.13657](https://arxiv.org/abs/2503.13657)

- DeepMind/MIT (2025). "Towards a Science of Scaling Agent Systems: When and Why Agent Systems Work." [arxiv.org/abs/2512.08296](https://arxiv.org/abs/2512.08296)

- PRISM (2026). "Expert Personas Improve LLM Alignment but Damage Accuracy: Bootstrapping Intent-Based Persona Routing with PRISM." [arxiv.org/abs/2603.18507](https://arxiv.org/abs/2603.18507)

- Hong, S., et al. (2024). "MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework." *ICLR 2024*. [proceedings.iclr.cc/paper_files/paper/2024/file/6507b115562bb0a305f1958ccc87355a-Paper-Conference.pdf](https://proceedings.iclr.cc/paper_files/paper/2024/file/6507b115562bb0a305f1958ccc87355a-Paper-Conference.pdf)

- Zamfirescu-Pereira, J.D., Wong, R.Y., Hartmann, B., Yang, Q. (2023). "Why Johnny Can't Prompt: How Non-AI Experts Try (and Fail) to Design LLM Prompts." *CHI 2023*. [dl.acm.org/doi/10.1145/3544548.3581388](https://dl.acm.org/doi/10.1145/3544548.3581388)

- ETH Zurich (2026). "Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?" [arxiv.org/html/2602.11988v1](https://arxiv.org/html/2602.11988v1)

- "Mind Your Tone: Investigating How Prompt Politeness Affects LLM Accuracy" (2025). [arxiv.org/abs/2510.04950](https://arxiv.org/abs/2510.04950)

### Official Documentation

- Anthropic. "Best Practices for Claude Code." [code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)

- Anthropic. "Prompting best practices" (Claude 4.6). [platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices)

- Anthropic. "How Anthropic Teams Use Claude Code." [www-cdn.anthropic.com/58284b19e702b49db9302d5b6f135ad8871e7658.pdf](https://www-cdn.anthropic.com/58284b19e702b49db9302d5b6f135ad8871e7658.pdf)

### Industry Analysis

- Forsythe, J. (2026). "10 Claude Code Principles." [jdforsythe.github.io/10-principles/overview/](https://jdforsythe.github.io/10-principles/overview/)

- HumanLayer. "Writing a Good CLAUDE.md." [humanlayer.dev/blog/writing-a-good-claude-md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)

- HumanLayer. "Skill Issue: Harness Engineering for Coding Agents." [humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents](https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents)

- VentureBeat. "Claude Code's source code appears to have leaked." [venturebeat.com/technology/claude-codes-source-code-appears-to-have-leaked-heres-what-we-know](https://venturebeat.com/technology/claude-codes-source-code-appears-to-have-leaked-heres-what-we-know)
