---
name: harness-rules
description: >
  Project rules and conventions for the Imperial Dragon workflow.
  Auto-invoked at session start to establish behavioral constraints:
  worktree isolation, git discipline, coding standards, and STATE.md format.
disable-model-invocation: false
user-invocable: false
---

# Imperial Dragon Harness — Rules

You MUST follow all rules in the companion reference files below.
These define non-negotiable behavioral constraints for every session.

Read and internalize each file before proceeding with any work:

1. **workflow.md** — Session start gate (worktree isolation), escalation protocol, when to ask the author, compaction rules.
2. **git.md** — Branch discipline, commit message standards, worktree lifecycle, PR workflow.
3. **coding-python.md** — Python 3.10+ style, testing markers, build patterns, dependency management. Load only when the project uses Python (pyproject.toml, setup.py, or *.py files present).
4. **state.md** — STATE.md format specification, pruning rules, section structure.
5. **tickets.md** — Ticket log verb set including bump categories, when to emit bump vs note.
