---
paths:
  - "tickets/"
  - "tickets/FORMAT.md"
last-reviewed: 2026-04-23
---

# Ticket log conventions — %erg v1

Tickets live in `tickets/` as `.erg` files. The log section is append-only.
Validate with `tickets/tools/go/erg check tickets/`.

## Log line format

```
{YYYY-MM-DDThh:mmZ} {actor} {verb} [{detail}]
```

Actor is typically `claude` or `haduong`. Detail is free text after the verb.

## Verbs (closed set)

| Verb | Usage |
|------|-------|
| `created` | Ticket was created |
| `status {new-status}` | Status changed; detail gives reason |
| `note {text}` | Free-form annotation; anything goes |
| `bump {category} — {detail}` | Agent paused waiting for a signal (see categories below) |

## Bump categories (closed set)

| Category | Meaning |
|----------|---------|
| `permission` | Harness blocked a tool call awaiting user approval |
| `author-decision` | Agent judged a call non-autonomous and stopped |
| `test-failure` | `make` / pytest / CI failed and blocked progress |
| `verify-reroll` | `/verify-gate` returned REROLL or ESCALATE |
| `circuit-breaker` | Orchestrator killed the agent (timeout, ping-pong, redirect ban) |

## When to emit bump vs note

- Use **`bump`** when the agent stopped and waited for a human signal — a real pause in autonomous flow.
  The category distinguishes trivial stoppages (permission, circuit-breaker) from hard ones (author-decision, test-failure).
- Use **`note`** for informational annotations that do not represent a stoppage.

Write bump lines to the main-repo ticket file at `~/.claude/tickets/{ticket}.erg`,
not to any worktree copy.

## Cross-worktree concurrency

The branch is the WIP signal: start work by creating a branch whose name
contains the ticket ID. No claim/release protocol — concurrent sweeps may
pick the same ticket and diverge onto different branches; the merge sorts
it out. Do not reintroduce a local lockfile.
