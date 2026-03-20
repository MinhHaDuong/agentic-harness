# Vision

A reusable harness for AI agent workflows — code and prose, day and night,
across LLMs, frameworks, and machines.

## Horizon

**Near-term: Overnight autonomous agent.**
Unsupervised sessions on a single machine (Claude Max). Picks up tickets,
works them through TDD, opens PRs for morning review. Self-paces around
rate limits. Recursive: when one braindump is exhausted, writes a new one.

**Mid-term: H24 ticket closer.**
Always-on background agent polling the ticket queue. Picks ripe tickets
(dependencies met, labels ready), starts work, escalates when stuck.
Runs continuously, not just overnight.

**Long-term: H24 generalist.**
Research + code + prose across multiple projects. Reads papers, drafts
manuscripts, runs analyses, manages submissions. The agent is a research
collaborator, not just a coder.

## Cross-cutting goals

### Multi-LLM

The harness must not be locked to one provider.

- **Claude Max** — primary, highest capability, rate-limited by plan tier
- **Ollama** (local) — free, private, GPU-bound (padme: A4000 + RTX 3060)
- **OpenRouter** — access to other models (Mistral, Qwen, etc.) at API prices

The same ticket, runbook, and skill should work regardless of which LLM
executes it. Model selection is a strategy decision (cost, capability,
privacy), not a framework constraint.

### Multi-framework

No lock-in to one coding agent either.

- **Claude Code** (VSCode, CLI, web, desktop) — current primary
- **Aider** — lightweight, git-native, multi-model
- **OpenCode** — terminal-based, Go
- **OpenHands** — cloud agents, GitHub Action integration
- **ZeroClaw** — emerging
- **GSD (Get Shit Done)** — meta-prompting harness, 29 skills

The harness provides the workflow (tickets, runbooks, skills, telemetry).
The framework provides the execution engine. They compose, not compete.

### Multi-machine

- **doudou** — development laptop, interactive work
- **padme** — remote GPU server, heavy computation, overnight runs
- **cloud** — future, for scaling beyond local hardware

The harness is a high-level orchestration layer. On padme it's one component
among others (GPU scheduling, model serving, data pipelines). It doesn't
try to be the whole system.

## Principles

**Offline-first.** Everything works without network. GitHub is a sync target,
not a dependency. Tickets are files, not API calls.

**Code and prose.** Research produces papers, not just software. The harness
handles manuscripts, slides, figures, and submissions alongside code.

**Accumulate data.** Instrument everything unobtrusively. Usage telemetry,
task metrics, model comparison data. The questions come later.

**Start simple.** Each module starts as a shell script or markdown file.
Complexity is earned by evidence, not anticipated by design.

## Modules

| Module | Status | Purpose |
|--------|--------|---------|
| Telemetry | Started | Usage tracking across all surfaces |
| Tickets | Dreaming | File-based, offline, gh-optional task tracking |
| Runbooks | In Oeconomia | Event-triggered workflow procedures |
| Skills | In Oeconomia | Composable agent capabilities with scripts/data |
| Hooks | In Oeconomia | Git hooks for quality gates |
| Guidelines | In Oeconomia | Coding and writing conventions as templates |
| LLM eval | Dreaming | Multi-model benchmarking on harness tasks |

Modules migrate here incrementally as they are generalized. The Oeconomia
project is the first user and proving ground.
