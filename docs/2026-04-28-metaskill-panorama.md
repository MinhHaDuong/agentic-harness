# The Metaskill Panorama — implications for IDH

**Date:** 2026-04-28
**Scope:** Thematic supplement to the 2026-04-04 review. Looks at what people in the Claude Code ecosystem mean when they say "metaskill" and what that lens reveals about IDH.
**Companion to:** [`20260404-review/00-synthesis.md`](20260404-review/00-synthesis.md). The earlier review covered hooks, settings hygiene, verification, and review personas. This report does not redo that work; it adds a single dimension the earlier sweep did not isolate.

> **Reader note (2026-04-29):** Every reference to `/orchestrator`
> below predates the rename to `/raid` (ticket 0045). The skill,
> recommendation R3, and the lifecycle-metaskill claim all still
> apply — only the slash command has changed.

---

## Résumé (FR)

« Métaskill » est devenu un terme valise. Cinq usages distincts coexistent dans l'écosystème Claude Code, et la plupart des recommandations applicables à IDH dépendent de la catégorie ciblée. Ce rapport propose une taxonomie en cinq classes (auto-tuning de configuration, observer/améliorateur, générateur de skills/agents, enseignant de configuration, orchestrateur de cycle de vie), situe IDH explicitement dans cette taxonomie, et ne propose que les ajouts qui correspondent au périmètre d'une harness mono-utilisateur. Trois recommandations concrètes : adopter le skill officiel `/fewer-permission-prompts` (résout C3 du 2026-04-04), ajouter un observer pour les sessions interactives (le canal manquant à côté de `nightbeat-report`), et formaliser `/orchestrator` comme métaskill dans la documentation.

---

## 1. The word "metaskill" means at least five different things

Surveying eight reference repositories and three commentaries (sources at end), the term covers five conceptually distinct patterns:

| # | Pattern | What it does | Reference |
|---|---------|--------------|-----------|
| **A** | **Configuration auto-tuner** | Reads session/transcript history, emits a diff to the harness configuration. | `/fewer-permission-prompts` (Anthropic, official) |
| **B** | **Observer / improver** | Silently logs friction during normal work; periodic review surfaces patterns; humans approve changes. | `rebelytics/one-skill-to-rule-them-all` (`task-observer`) |
| **C** | **Skill / agent generator** | Produces new SKILL.md files, subagent definitions, or whole agent teams. | `xvirobotics/metaskill`, `obra/superpowers/writing-skills`, `FrancyJGLisboa/agent-skill-creator` |
| **D** | **Configuration teacher** | Teaches Claude *about Claude Code itself* (skills, hooks, MCP, permissions) so users can be guided through configuration. | `werkamsus/claude-metaskill` |
| **E** | **Lifecycle orchestrator** | Runs existing skills in sequence to drive a multi-phase workflow end-to-end. | IDH `/orchestrator`, `/beat`, `obra/superpowers/executing-plans` |

These do not collapse into one another. A generator (C) creates artifacts; an observer (B) creates *recommendations* that humans turn into artifacts; an auto-tuner (A) creates a constrained, verifiable diff against a known config schema; an orchestrator (E) runs nothing new — it sequences what exists. Conflating them produces unfocused recommendations.

A second observation about the panorama itself: the population of "metaskills" is heavily biased toward C (generators) and D (teachers). Both presume the user does not yet have a harness. IDH already has one. That immediately rules out half of the panorama as scope-mismatched.

---

## 2. Where IDH already sits

IDH covers three of the five categories already, two implicitly:

| Pattern | IDH surface | Status |
|---------|-------------|--------|
| **A** Auto-tuner | None — `settings.local.json` is curated by hand. The 2026-04-04 synthesis flagged this as finding C3 (140 lines of accumulated one-off permissions). | **Gap** |
| **B** Observer | Three partial surfaces: `nightbeat-report` Step 4 (autonomous-channel only, post-hoc, structured), `celebrate` Step 11 ("Offer to improve workflow rules if lessons were learned" — per-task, suggestion), `memory` sweep (TTL-managed, semantic). No surface logs interactive-session friction structurally. | **Partial** |
| **C** Generator | `new-ticket` generates ticket scaffolds. No skill creates other skills. | **Out of scope** |
| **D** Teacher | `harness-rules` (companion `.md`s) auto-loads at session start. Functional, but inverts the progressive-disclosure pattern Anthropic recommends — it teaches by being always-loaded, not by being discoverable on demand. | **Architecturally different** |
| **E** Orchestrator | `/orchestrator` (171 lines) runs the Five Claws across N tickets autonomously. `/beat` is its single-cycle wrapper. `/verify` runs a sub-orchestration of adherence + review + gate. | **Strong — defining feature of IDH** |

The strongest IDH-specific observation: **`/orchestrator` is a lifecycle metaskill in the (E) sense, but it is not labelled as one anywhere in the README or harness-rules.** It is currently described as "Run Imperial Dragon batch across multiple tickets." That is operational, not categorical. The label matters because users searching for a metaskill pattern in IDH won't find it under that description.

---

## 3. Findings against the panorama

### F1. The interactive observer is the only real metaskill gap

`nightbeat-report` covers the autonomous channel comprehensively — six categories of friction patterns (permission denials, budget exhaustion, recurring tickets, ambiguous orchestrator outputs, idle projects, expensive stuck tickets), with concrete fix proposals per pattern. It is a strong example of pattern (B), but it only fires after `claude-nightbeat.timer` runs.

Interactive sessions — the bulk of IDH usage — produce no equivalent structured log. `celebrate` Step 11 is a one-line nudge ("Offer to improve workflow rules if lessons were learned"). It depends on the model deciding to surface lessons; it does not append to a durable log; it does not trigger a periodic aggregate review. `task-observer`'s key contribution over IDH's existing surface is the **silent-log-plus-weekly-review** pattern: every session adds observations to a JSONL, and once a week (or after N entries) an aggregate sweep proposes harness changes.

This is a closable gap. IDH already has the JSONL convention (`celebrations.jsonl`, 46 entries, ~25 days of data). Adding `observations.jsonl` and a weekly aggregator skill costs a few hundred lines and reuses the existing telemetry-directory pattern.

### F2. `/fewer-permission-prompts` directly resolves an open finding

Anthropic shipped this skill (Boris Cherny announced it 2026-Q1). It scans the user's session transcript for bash and MCP commands that are safe but caused repeated permission prompts and emits a recommended allowlist diff against `.claude/settings.json`. This is a textbook pattern (A) auto-tuner.

It maps one-to-one onto the 2026-04-04 finding **C3** ("`settings.local.json` is bloated — 140 lines of accumulated one-off permissions including `sudo tee:*`, `sudo cp:*`. Not a curated policy"). The earlier review's recommendation **T3** was "Audit and prune `settings.local.json` — remove one-offs, narrow `sudo` grants, document policy." `/fewer-permission-prompts` automates the first half of T3 against fresh transcript evidence. The "document policy" half remains manual.

Caveat: there is one known bug. The skill strips environment-variable prefixes during extraction, so commands of the shape `TEST_DATABASE_URL="..." uv run pytest` are missed (`anthropics/claude-code` issue #51057). For IDH's use case — which has many `make` and `uv run` invocations — this matters but does not invalidate adoption.

### F3. SKILL.md description audit returns a clean bill of health

The current best-practice rule from Anthropic and from Lee Hanchung's first-principles essay is that descriptions should be action-oriented ("Use when…", with specific task verbs). Vague capability lists prevent discovery; kitchen-sink descriptions defeat progressive disclosure.

A pass over IDH's 26 skill descriptions (extracted by `awk` from frontmatter) finds them mostly compliant: they lead with imperative verbs (`Trigger`, `Merge`, `Pick`, `Create`, `Begin`, `Claim`, `Close`, `Run`, `Check`, `Validate`, `Re-resolve`, `End-of-day`, `Post-task`, etc.) and they specify the trigger condition by context (e.g., `verify-gate`: "Validates every ticket exit criterion and every review comment against the actual diff. Emits APPROVED / REROLL / ESCALATE…").

Two minor exceptions worth noting (not fixing — these are genuine edge cases):

- `harness-rules` uses `description: >` (folded YAML) — likely a multi-line description. By design this skill *should* always load (it's the rules file). If Anthropic's progressive-disclosure model rewards descriptions that match user intent, an always-loaded skill has no intent to match. This is the architectural mismatch flagged in §2 row D, not a bug.
- `smoke` description ("Agent environment smoke test — reports runtime identity, auth method, and harness context") is descriptive rather than imperative ("Use when verifying…"). Low-stakes — `smoke` is rarely invoked.

The clean bill is itself a finding: it suggests the implicit description-style discipline (likely inherited from harness-rules' brevity culture) is doing real work without being stated as a rule.

### F4. The `harness-rules` pattern is not progressive disclosure

`harness-rules` loads its companion `.md` files (workflow, git, tickets, state, coding-python — 204 lines total) at session start regardless of task. Anthropic's documented model is the inverse: SKILL.md frontmatter is the only thing always loaded; the body and references are loaded on demand when the description matches.

Two ways to read this:

1. **The Anthropic model is wrong for rules.** Rules are universally applicable; loading them on demand introduces uncertainty about whether the rule fires. This is the case the harness-rules pattern bets on.
2. **The Anthropic model is right and harness-rules is paying a context tax.** 204 lines of rules occupy ~1500 tokens of every session, whether the session is one ticket close or a deep refactor. Lee Hanchung's anti-pattern list explicitly names "kitchen-sink skills" and "embedding verbose documentation in SKILL.md" as the pattern that defeats progressive disclosure.

Empirically, IDH's session counts are healthy and the harness has measurably improved over the year (46 celebrations across 8 projects, 25 active skills shipped). That is weak evidence that interpretation #1 holds in practice. But it does not prove the rules are pulling their context-tax weight; an A/B with rules behind progressive disclosure (`workflow.md` loads on session-start mention; `coding-python.md` loads only on .py edits; `tickets.md` loads only when a ticket verb fires) would.

This is a research question, not an action item. Flagging because the panorama specifically rejects always-loaded patterns and IDH should know it is making a counter-bet.

### F5. Patterns the panorama offers that IDH should *not* adopt

The panorama is a buffet, not a checklist. Three patterns are popular in the ecosystem but mismatched to IDH:

- **Team-generation metaskills (xvirobotics/metaskill, generated `tech-lead` + `specialists` + `code-reviewer`).** IDH is a single-user research harness; a generated agent team adds coordination overhead that pays back only on multi-developer projects.
- **Prompt-enrichment hooks (severity1/claude-code-prompt-improver, ckelsoe/prompt-architect).** These rewrite vague user prompts into structured CO-STAR / RISEN / etc. frames before Claude executes. IDH's terseness culture (the 87-line rules budget, the "Mind Your Tone" finding from 2026-04-03) is a deliberate counter-bet against verbose prompt scaffolding.
- **Configuration-teacher metaskills (werkamsus/claude-metaskill).** Useful for users still learning Claude Code; redundant for the IDH author.

Naming these is part of the contribution — it forecloses obvious future "should we add X?" branches.

---

## 4. Recommendations

Three concrete actions, ranked by leverage. None duplicate the 2026-04-04 action plan.

### R1 (Tier 1) — Adopt `/fewer-permission-prompts` and run it on doudou

**What:** Run the official Anthropic skill against the current session-history corpus to generate an allowlist diff for `settings.local.json`. Review, prune one-offs (per 2026-04-04 T3), commit the pruned file.

**Why:** Closes the bottom half of finding C3 from 2026-04-04 with vendor-supported tooling. Pattern-(A) auto-tuners are the only metaskill class IDH currently lacks entirely.

**Caveat:** Watch for the env-var-prefix bug on `make`/`uv run` invocations; verify the diff manually before applying.

**Out:** A pruned, justified `settings.local.json` and a one-line policy note in the harness CLAUDE.md ("permissions allowlist is regenerated quarterly via `/fewer-permission-prompts`").

### R2 (Tier 2) — Add an interactive-session observer

**What:** A new skill `/observe` (or a hook) that appends one line per session-end to `~/.claude/telemetry/observations.jsonl` capturing friction patterns: tool denials encountered, retries, instructions ignored, manual workarounds. Pair it with a weekly aggregator that runs from the existing `claude-nightbeat.timer` and emits a harness-improvement digest analogous to `nightbeat-report` Step 4 but for the interactive channel.

**Why:** Closes the only real gap in IDH's observer coverage (F1). Reuses the existing telemetry directory and JSONL convention. Inspired by `rebelytics/one-skill-to-rule-them-all`'s silent-log-plus-weekly-review pattern, but feeds IDH's existing aggregation pipeline rather than introducing a parallel one.

**Out of scope:** Auto-applying the proposed changes. Observations go to a log; humans approve; humans edit. This matches the conservative posture in `task-observer`'s design note ("never modifies skills directly").

**Open question:** What goes in the observation log entry? Minimum viable: timestamp, session-id, project, three free-text fields (issue / suggested fix / generalisable principle). The `task-observer` schema is a good starting reference.

### R3 (Tier 3) — Document `/orchestrator` as IDH's lifecycle metaskill

**What:** One sentence in README.md and one section in `harness-rules/workflow.md` naming `/orchestrator` (and `/beat` as its single-cycle invocation) as IDH's metaskill — the skill that runs other skills. Cross-link `/verify`, which is a sub-orchestrator, in the same place.

**Why:** Discoverability. Users (and future-Claude reading the harness for the first time) will look for the entry point. Right now the description ("Run Imperial Dragon batch across multiple tickets") buries the categorical role under the operational summary.

**Cost:** Two paragraphs. No code change.

**Non-goal:** Don't promote `/orchestrator` into a generator (pattern C) or observer (pattern B). Lifecycle orchestration is a different metaskill class and conflating them is exactly the trap §1 warns against.

---

## 5. Open questions for follow-up

These don't fit into actions but are worth a future doc:

- **Is `harness-rules`' always-loaded design paying for itself?** §F4 frames this. An A/B over a week of session telemetry (rules loaded vs. rules behind progressive disclosure) would settle it. Current evidence is suggestive but not conclusive.
- **Should `/celebrate` Step 11 be replaced by R2 (the observer log)?** They overlap. Either Step 11 stays as the synchronous "do you want to update rules?" prompt and the observer captures the silent residue, or Step 11 is dropped in favor of the observer's aggregate review. Probably the former, but worth deciding.
- **Should the harness publish a skills-search tool?** `obra/superpowers` ships `skills-search` as the discovery surface for its 20+ skills. IDH has 26 skills and a flat `/<skill-name>` namespace; a search tool would matter once the count exceeds ~40. Not now.

---

## 6. Sources

Primary references consulted:

- [Anthropic — Agent Skills overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) — three-level loading model, progressive disclosure, description format requirements.
- [Anthropic — Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — anti-patterns (kitchen-sink, vague descriptions).
- [Boris Cherny / Anthropic — `/fewer-permission-prompts` announcement](https://www.threads.com/@boris_cherny/post/DXM_ATCjwKj) — pattern (A) reference implementation.
- [`anthropics/claude-code` issue #51057](https://github.com/anthropics/claude-code/issues/51057) — env-var-prefix bug in the auto-tuner.

Community / third-party:

- [`rebelytics/one-skill-to-rule-them-all`](https://github.com/rebelytics/one-skill-to-rule-them-all) — pattern (B) reference. CC BY 4.0.
- [`werkamsus/claude-metaskill`](https://github.com/werkamsus/claude-metaskill) — pattern (D).
- [`xvirobotics/metaskill`](https://github.com/xvirobotics/metaskill) — pattern (C), team generation variant.
- [`FrancyJGLisboa/agent-skill-creator`](https://github.com/FrancyJGLisboa/agent-skill-creator) — pattern (C), cross-platform variant.
- [`obra/superpowers`](https://github.com/obra/superpowers) — pattern (E) plus a `writing-skills` meta-skill in pattern (C).
- [`severity1/claude-code-prompt-improver`](https://github.com/severity1/claude-code-prompt-improver) — pattern not adopted (rejected, §F5).
- [Lee Hanchung — Claude Agent Skills: A First Principles Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/) — discovery mechanism, anti-patterns.
- [Massively Parallel Procrastination — Skills for Claude!](https://blog.fsck.com/2025/10/16/skills-for-claude/) — composition wishlist and TDD-for-skills.

Internal (companion documents):

- [`docs/20260404-review/00-synthesis.md`](20260404-review/00-synthesis.md) — comprehensive review, this report supplements not duplicates.
- [`docs/2026-04-03-harness-best-practices-research.md`](2026-04-03-harness-best-practices-research.md) — evidence base for context-hygiene and verification claims.
- `~/.claude/telemetry/celebrations.jsonl` — 46 entries, 2026-03 to 2026-04, basis for the JSONL-aggregator pattern reuse argument.
