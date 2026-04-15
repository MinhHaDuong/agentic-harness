---
name: new-ticket
description: Create a ticket as a handoff document with required sections for TDD workflow.
disable-model-invocation: false
user-invocable: true
argument-hint: [title]
---

# New ticket

`[Imagine → Plan]`

Tickets are handoff documents. A new agent will only have the context provided.

## Required sections

```markdown
## Context
What problem or need this addresses. Why now.

## Relevant files
- `path/to/file.py` — role in this task

## Actions
1. Concrete step
2. Concrete step

## Test
- What test to write first (red step of TDD)

## Verification
- [ ] How to confirm each action worked

## Invariants
- What must not break (tests, build, existing behavior)

## Exit criteria
- Definition of done — when is this ticket complete?
```

Create the ticket using whatever system the project has (git-erg `tickets/` directory preferred, forge issues as fallback). The agent knows how to use the available tools.

## Tracking ticket convention

When investigation spawns sub-tickets:

1. Original ticket becomes the **tracking ticket** — leave it open.
2. Create each sub-ticket referencing the tracker.
3. Edit tracking ticket to list each child.
4. Tracking ticket closes only after integration review (see `/celebrate` step 11).
