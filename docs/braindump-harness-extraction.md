# Harness extraction braindump

Transferred from Oeconomia project (`docs/braindump-harness-extraction.md`) on 2026-03-20.
Original written 2026-03-19. Git history in the source repo has earlier versions.

## 1. Split the harness into its own repo

**Status: started.** This repo (`agentic-harness`) is the result. Telemetry is the first module.

**What will move (incrementally):**
- `AGENTS.md` (becomes the new repo's core doc)
- `runbooks/` (the full trigger system)
- `hooks/` (pre-commit, post-checkout)
- `Makefile` targets related to workflow (`make setup`, `make check`, `make check-fast`)
- `docs/coding-guidelines.md`, `docs/writing-guidelines.md` (as templates)
- The Dragon Dreaming phase model documentation

**What stays in projects:**
- `CLAUDE.md` pointing to a lightweight local `AGENTS.md` that `@includes` the harness
- Domain-specific content, data, scripts
- Journal-specific style guides
- `STATE.md`, `ROADMAP.md` — project-specific

**Open questions:**
- **Consumption model**: git submodule? Template repo you fork? Package you install?
- **Customization points**: how to separate framework from project config?

## 2. Review harness against seminal software engineering books

Intellectual audit — positioning what we've built against the canon.

| Book | Key idea | Harness connection |
|------|----------|-------------------|
| **Programming Pearls** (Bentley) | Problem decomposition, test-first thinking | TDD Red/Green/Refactor cycle, `make check-fast` |
| **Code Complete** (McConnell) | Construction as craft, checklists | Runbooks as checklists, pre-commit hooks as guardrails |
| **Extreme Programming Explained** (Beck) | Small releases, continuous integration, courage | Wave cycles, one-change-per-commit, escalation ladder |
| **The Mythical Man-Month** (Brooks) | Conceptual integrity, surgical team | One ticket per conversation, agent identity, Dreaming phase |
| **The Pragmatic Programmer** (Hunt & Thomas) | DRY, tracer bullets, orthogonality | Runbook triggers, hook system, worktree isolation |
| **Refactoring** (Fowler) | Small behavior-preserving transformations | Red/Green/Refactor, one change per commit |
| **Test-Driven Development** (Beck) | Red-green-refactor as design technique | Core of the Doing phase |
| **A Philosophy of Software Design** (Ousterhout) | Deep vs shallow modules, complexity as enemy | Phase separation, one ticket per conversation |
| **The Design of Everyday Things** (Norman) | Affordances, error prevention | Pre-commit hooks, triggers as affordances |
| **Peopleware** (DeMarco & Lister) | Flow, team chemistry | Celebrating phase, feedback memories |
| **Clean Code** (Martin) | Readability, single responsibility | Why-not-what commit messages, branch naming |
| **SICP** (Abelson & Sussman) | Abstraction barriers, metalinguistic abstraction | The harness itself is a metalinguistic abstraction |
| **The Art of Unix Programming** (Raymond) | Rule of Modularity, Rule of Composition | Makefile pipeline, DVC DAG, separation of concerns |
| **Lean Software Development** (Poppendieck) | Eliminate waste, defer commitment | Wave cycles, Dreaming phase, feedback memories |
| **Managing the Design Factory** (Reinertsen) | Queuing theory, batch size | Small commits, wave cycle as cadenced flow |

Could become a "Design Rationale" or "Intellectual Lineage" document.

## 3. Offline ticket system — file-based, gh-optional

Ticket = markdown document as the primitive, GitHub Issues as one backend.
The system handles **code AND prose** — research papers, not just software.

### Format: YAML frontmatter + markdown body

```markdown
---
id: 42
title: Refactor classify_type complexity
labels: [triage/now, techdebt]
status: open  # open | in-progress | done
branch: t42-classify-type
depends: []
created: 2026-03-19
---

## Context
...

## Actions
...

## Exit criteria
...

## Conversation log
...
```

YAML frontmatter for structured metadata (labels, status, dependencies),
markdown body for description and conversation. This mirrors GitHub Issues
(structured fields + free-text body) without requiring their API.

### Existing practices to review

- **GitHub Issues** (YAML-ish via labels/milestones, free-text body)
- **GitLab issues** (similar, supports `/commands` in comments)
- **Linear** (structured tickets, markdown descriptions)
- **Plain markdown tickets** (used successfully in Oeconomia wave planning)
- **Obsidian/Logseq** (YAML frontmatter + markdown, task management plugins)
- **todo.txt** (plain text, structured by convention)
- **Org-mode** (outline-based, properties drawers for metadata)
- **Issue-as-code**: [git-bug](https://github.com/MichaelMure/git-bug),
  [git-issue](https://github.com/dspinellis/git-issue) — store issues in git itself

The YAML frontmatter approach is closest to Obsidian/Jekyll conventions and is
already familiar from Quarto, Hugo, and static site generators.

### Proposed convention

```
tickets/
  042-classify-type.md       # open ticket
  done/042-classify-type.md  # completed (moved after merge)
```

- `start-ticket` reads from `tickets/NNN-*.md` instead of `gh issue view NNN`.
- `celebrate.md` moves the file to `done/` and appends a completion summary.
- When `gh` is available, a sync script can push/pull between local files and GitHub Issues.

### What we lose without GitHub

Current usage across MinhHaDuong repos (as of 2026-03-20):
- **Oeconomia**: 30 issues, 30 PRs — heavy user of issues and PRs
- **sdg7evn**: 12 issues, 0 PRs — issues only
- **nvfd, dotfiles**: issues disabled
- **aedist, VinaPyPSA**: minimal (0-2 issues)

Features actually used: issues (descriptions, labels, triage/* labels), PRs
(review, diff, merge). Not used: milestones, projects/boards, webhooks,
sub-issues.

**Keep:** Labels (in frontmatter), issue-PR linking (branch name convention).
**Don't need:** Milestones, projects, webhooks.
**PRs stay on GitHub** — diff review and merge workflow has no good local
equivalent. The ticket system is for planning; PRs are for execution review.

## 4. Skill-based agent coordination

Replace fixed agent perspective tables with composable skill pool:
- **Skills**: atomic markdown files (one sentence scope + instructions).
  May include scripts and reference data (e.g., a journal spec skill bundles
  the style guide PDF + a checking script).
- **Experts**: named skill bundles + perspective (yaml).
  E.g., `reviewers/security.yaml` = skills `[owasp-top10, dependency-audit, secret-scan]` + perspective "adversarial".
- **Coordinators**: runbooks assemble purpose-built teams per event.
- Academic metaphor: skill=expertise, expert=reviewer, coordinator=editor.

### Skills vs runbooks

| | Skills | Runbooks |
|---|--------|---------|
| **Triggered by** | Invoked on demand (`/skill-name`) | Triggered by events (on-start, pre-commit) |
| **Contains** | Knowledge + instructions, optionally scripts/data | Procedural steps, checklists |
| **Scope** | One capability ("review for security", "format Oeconomia style") | One workflow ("start a ticket", "celebrate completion") |
| **Composable** | Yes — experts bundle multiple skills | No — runbooks are standalone procedures |
| **Example** | `skills/journal-scientific-data/` with author guidelines + checker | `runbooks/review-pr.md` with step-by-step review procedure |

### Sweep disk for skills

Existing skills scattered across machines and surfaces:
- Claude web interface: custom instructions, project knowledge files
- `~/.claude/commands/` or project `.claude/commands/`: Claude Code custom commands
- Project-specific `skills/` directories if any
- Writing guidelines, coding guidelines = skills in disguise

Action: inventory all of these, repatriate into `skills/` in this repo as canonical home.

## 5. Background ticket poller

A background agent that watches the ticket queue (GitHub Issues or `tickets/`
directory), picks ripe tickets (dependencies met), and starts work or alerts.
Automating the "Select" step of the wave cycle.

## 6. Type assertion guidelines — light touch

**Core principle: defensive effort proportional to risk.**

| Risk level | Example | Appropriate defense |
|------------|---------|-------------------|
| Low | Local script, single-use | Docstring, maybe a return type hint |
| Medium | Shared utility, pipeline step | Function signatures typed, key asserts, basic tests |
| High | Library consumed by others | Full type hints, validation at entry points, thorough tests |

Key rules:
- Use where they clarify intent, skip where they add noise
- Validate at system boundaries, trust internal code
- Modern stable Python (3.10+): `list[str]`, `X | None`, no `from __future__`
- No ABC classes — use Protocol if you need a contract
- No type-level gymnastics for research scripts

## 7. Script hygiene defaults

- **One output, one script**: 1 figure = 1 script file
- **Unix-style I/O**: default to stdin/stdout, optional `-i`/`-o` args
- **Log, not print**: all diagnostics through `logging` to stderr

## 8. Sweep disk for reusable guidelines

Harvest conventions from past projects: UTF-8, logging patterns, EditorConfig,
pyproject.toml, git hooks, .env patterns.
