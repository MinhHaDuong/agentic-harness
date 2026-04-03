# Review 5: Evidence-Based Best Practices — Deep Research Report

**Date:** 2026-04-03 (research) / 2026-04-04 (filed)
**Reviewer:** Opus agent (web deep research)

*Full report saved separately at `docs/2026-04-03-harness-best-practices-research.md`*

---

## Key Findings Summary

### Highest-Confidence Results (peer-reviewed, quantified)

| Finding | Source | Measured Impact |
|---------|--------|-----------------|
| Mid-context placement kills accuracy | Liu et al., TACL 2024 | **30%+ accuracy drop** |
| Independent multi-agent systems amplify errors | DeepMind/MIT, 2025 | **17.2x error amplification** |
| Expert personas damage factual accuracy | PRISM, 2026 | **3.6pp accuracy loss** |
| LLM-generated context files hurt performance | ETH Zurich, 2026 | **-0.5 to -3% success rate, +14-22% token cost** |
| Structured planning artifacts reduce errors | MetaGPT, ICLR 2024 | **~40% fewer errors** |
| Verification failures dominate multi-agent failures | MAST, 2025 | **23.5% of all failures; +15.6% from enhanced verification** |
| 5-agent team: 7x cost, 3.1x output | DeepMind, 2025 | **0.44 efficiency ratio** |
| >45% single-agent accuracy → adding agents hurts | DeepMind, 2025 | **β=-0.408, p<0.001** |

### Imperial Dragon Harness Assessment

**Scores well above average:**
- 87 lines total (most community harnesses: 200-500+)
- No flattery, no over-specification, no agent proliferation
- Hooks for deterministic enforcement
- Worktree-per-session isolation
- Tiered verification (`make check-fast` / `make check`)

### Evidence-Backed Recommendations for the Harness

| Priority | Recommendation | Evidence |
|----------|---------------|----------|
| High | Reduce `effortLevel` from `max` to `high` | Anthropic warns `max` on Opus 4.6 causes excessive exploration |
| High | Add compaction survival instruction (1 line) | Anthropic best practices for long sessions |
| Medium | Add subagent usage guidance | Anthropic: Opus 4.6 "has strong predilection for subagents" |
| Medium | Move Python type syntax rules to ruff config | ETH Zurich: every instruction adds token overhead |
| Low | Add adversarial review prompting guidance | MAST: sycophancy is top quality failure |
| Low | Add living documentation freshness check | Forsythe Principle 3 |

### Sources

8 peer-reviewed papers, 3 official Anthropic docs, 4 industry analyses. Full citations in the detailed report.
