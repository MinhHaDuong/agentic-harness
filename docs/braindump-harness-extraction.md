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

**Proposed convention:**
```
tickets/
  NNN-short-title.md       # open ticket
  done/NNN-short-title.md  # completed (moved after merge)
```

**Why:**
- Zero external dependencies. Works in any sandbox, container, or CI.
- Tickets versioned in git. Agents can create without auth tokens.
- Hybrid model: local files as source of truth, gh sync when available.

**What we lose without GitHub:** Web UI, labels, milestones, project boards, webhooks.

## 3b. Skill-based agent coordination

Replace fixed agent perspective tables with composable skill pool:
- Skills: atomic markdown files (one sentence scope each)
- Experts: named skill bundles + perspective (yaml)
- Coordinators: runbooks assemble purpose-built teams per event
- Academic metaphor: skill=expertise, expert=reviewer, coordinator=editor

## 3c. Background ticket poller

A background agent that watches the ticket queue, picks ripe tickets (dependencies met), and starts work or alerts. Automating the "Select" step of the wave cycle.

## 4. Type assertion guidelines — light touch

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

## 5. Script hygiene defaults

- **One output, one script**: 1 figure = 1 script file
- **Unix-style I/O**: default to stdin/stdout, optional `-i`/`-o` args
- **Log, not print**: all diagnostics through `logging` to stderr

## 6. Sweep disk for reusable guidelines

Harvest conventions from past projects: UTF-8, logging patterns, EditorConfig, pyproject.toml, git hooks, .env patterns.

## Codebase review findings (2026-03-19)

From audit of Oeconomia pipeline (63 scripts, ~19k lines):

**Works well:** Zero classes, no security smells, consistent `get_logger()`, f-strings dominant.

**Remaining issues:**
1. `utils.py` is 717-line god module (logging, retries, paths, checkpointing)
2. Plotting scripts have 200-400 line functions
3. Hardcoded constants across 20+ scripts

| Metric | Value |
|--------|-------|
| Total scripts | 68 |
| Average length | ~308 lines |
| Longest | `collect_syllabi.py` (855 lines) |
| Classes | 0 |
| Functions >50 statements | 22 |
| Test files | 27 |

## Arc

Six ideas forming a coherent sequence: extract the methodology (1), validate intellectually (2), operationalize it (3), add sensible defaults (4+5+6).
