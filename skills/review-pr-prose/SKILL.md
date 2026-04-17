---
name: review-pr-prose
description: Simulated peer review panel for manuscript prose. Spins discipline-specific agents for multi-perspective review.
disable-model-invocation: false
user-invocable: true
argument-hint: <pr-number>
context: fork
---

# Review PR prose $ARGUMENTS — simulated peer review panel

Spin disciplinary agents in parallel, each in a fresh context. Prose review reads **full text**, not just diff.

## Setup

1. Identify the text: which `.qmd`/`.md` files changed? What is the target venue?
2. Read the diff of the merge request.
3. Recruit the panel: select agents appropriate for the venue and scope of changes. Always include an adversarial referee. Add a journal-specific expert if venue rules exist (check project rules).

## Each agent runs

1. Read the **full text** (not just the diff).
2. Report **confidence** + **severity** (major / minor / suggestion).
3. Verdict: **accept**, **minor revision**, or **major revision**.

Agents with relevant expertise should use available tools (web search for literature, linting tools if installed, etc.).

## AI-tells auditor (always included)

One agent is always the **AI-tells auditor**. It reads `config/ai-tells.yml` for blacklisted words, phrases, conditional words, density limits, and patterns to flag. It scans the full text (not just the diff) and reports every violation with line number, context, and severity. This agent has no other role — it is a specialized lint pass.

## Synthesis

1. Preserve dissent verbatim.
2. Group findings: major (blocks acceptance), minor (should fix), suggestion.
3. Deduplicate convergent findings.
4. Build the manuscript. Check consistency between prose and data.
5. Post a single review on the merge request.

## Minor/suggestion tags (mandatory)

Every minor or suggestion item in the posted review carries exactly one prefix:

| Prefix | Meaning |
|---|---|
| `verifiable:` | A reproducible check is attached (line-number citation against the text, numeric recheck, lint rule violation). Reviewer can confirm without re-reading the paragraph. |
| `consider:` | Hypothesis or taste call. No enforcement. Author may dismiss. |
| `nofollow:` | Noted but not pursued (out of venue, already handled elsewhere, deliberate stylistic choice). No action expected. |

Rules:
- Hedged prose like "readers may find X confusing" without a concrete pointer is forbidden. Either cite the line and the confusable construction (`verifiable:`) or downgrade to `consider:`.
- Majors are not tagged; tags are for the minor/suggestion tier only.

## Proportional depth

| Text change | Panel size |
|---|---|
| Typo, citation fix | Copy editor only |
| Section rewrite | 3 agents (domain + adversarial + copy) |
| Full paper draft | Full panel (5-6 agents) |
| Submission-ready | Full panel + response-to-reviewers template |
