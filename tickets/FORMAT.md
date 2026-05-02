# Ticket format spec — %erg v1

## Overview

Local ticket system for agent coordination across worktrees and machines.
Not a replacement for GitHub Issues — those handle inter-agent and human coordination.
Tickets are committed to git and travel with the repo.

## File format

Extension: `.erg`
Location: `tickets/` (active), `tickets/archive/` (closed, old)
Encoding: UTF-8, LF line endings.

### Magic first line

```
%erg v1
```

Every `.erg` file starts with this line. It declares the format version
and enables file-type detection without relying on the extension. A future
`%ticket v2` adds headers without breaking v1 validators (they reject
unknown versions rather than silently misparsing).

### Structure

```
%erg v1
Title: Short imperative description
Status: open
Created: 2026-03-27
Author: claude

--- log ---
2026-03-27T10:00Z claude created

--- body ---
Free-form markdown body.
```

Three sections, in order:
1. **Headers** — RFC 822 style, one per line, immediately after magic line.
2. **Log** — append-only ledger, after `--- log ---` separator.
3. **Body** — free-form markdown, after `--- body ---` separator.

A blank line ends the header block. Both separators are required (the
validator rejects files missing either one).

### Headers (closed set, v1)

| Header | Required | Type | Values |
|--------|----------|------|--------|
| `Title` | yes | string | Short imperative sentence |
| `Status` | yes | enum | `open`, `closed` |
| `Created` | yes | date | `YYYY-MM-DD` |
| `Author` | yes | string | Agent or human identifier |
| `Blocked-by` | no | ref | Ticket ID or `gh#N` (repeatable) |

No other headers are valid in v1. No `X-` extensions. If v2 needs new
headers, it declares `%ticket v2` and extends the set.

**Status values:**
- `open` — available for work (subject to branch-as-claim check).
- `closed` — completed or cancelled.

**`Blocked-by` references:**
- A 4-digit ID (e.g., `0041`) refers to a local ticket.
- `gh#N` refers to a GitHub issue. Resolved via API when online, treated as
  satisfied (non-blocking) when offline.
- Repeatable: one `Blocked-by:` line per dependency.
- A blocker must be `closed` to unblock.

### ID assignment

The ticket ID is derived from the filename, not a header.

Filename pattern: `{ID}-{slug}.erg`
- ID: zero-padded sequential number, 4 digits. `0001`, `0002`, ...
- Slug: lowercase kebab-case, ASCII only (`[a-z0-9-]`).

To assign the next ID: read filenames in `tickets/` and `tickets/archive/`,
extract the numeric prefix from each, take the maximum, increment by 1,
zero-pad to 4 digits. If no tickets exist, start at `0001`.

**Collision handling:** optimistic. Two worktrees may pick the same number.
The pre-commit validator catches duplicate IDs. The agent that loses renames
its ticket (increment again). This matches git's own optimistic concurrency.

### Log section

Append-only. Each line records one event:

```
{ISO-8601-timestamp} {actor} {verb} [{detail}]
```

**Timestamp:** `YYYY-MM-DDThh:mmZ` (UTC, minute precision).
**Actor:** agent or human identifier (e.g., `claude`, `user`).
**Verbs (closed set, v1):**

| Verb | Meaning |
|------|---------|
| `created` | Ticket created |
| `status` | Status changed. Detail: new status + reason |
| `note` | Free-form annotation |
| `bump {category} — {detail}` | Agent paused waiting for a human signal. Category is mandatory and must be one of: `permission`, `author-decision`, `test-failure`, `verify-reroll`, `circuit-breaker`. |

Lines are never edited or deleted. To correct an error, append a new line.

### Body section

Free-form markdown. Convention for actionable tickets:

```
## Context
Why this work exists.

## Actions
1. Concrete steps.

## Test
First test to write (TDD red step).

## Exit criteria
Definition of done.
```

Not enforced by the validator. Agents are encouraged to follow the convention
but the body is structurally unconstrained.

## Ticket state model

### Claim signal: branch-as-claim

A ticket is **in progress** (claimed) iff a branch whose name contains the
4-digit ticket ID exists. No `.wip` files. No `Status: doing`.

```
git branch --list "*{id}*"       # local — always authoritative
git branch -r --list "*{id}*"   # remote — cross-machine, best-effort
```

Branch naming is free-form as long as the ID appears somewhere:
`fix/0066-...`, `0066-state-model`, `worktree-0066-foo` all work.

**Offline safety:** if the remote check fails, treat as "no remote claim"
and continue. A beat is never blocked by a network failure.

### State tuple and valid states

State: `(Status, local_branch, remote_branch)`
where `local_branch` = any local branch name contains the ID,
`remote_branch` = same for remote (best-effort).

| Status | local | remote | Name | Meaning |
|--------|-------|--------|------|---------|
| open | — | — | AVAILABLE | Ready to pick |
| open | ✓ | — | CLAIMED | Active, not yet pushed |
| open | ✓ | ✓ | IN_PROGRESS | Active, cross-machine visible |
| open | — | ✓ | REMOTE_CLAIM | Another machine working; do not pick |
| closed | — | — | DONE | Complete, branches cleaned |
| closed | ✓/— | ✓/— | POST_MERGE | Branch cleanup pending; transient, benign |

### Coherence rules

- **R1:** Claimable iff `Status: open` AND no branch with ID exists (local or remote).
- **R2:** Done iff `Status: closed`. Branch cleanup is housekeeping, not a
  correctness condition.
- **R3:** All scheduling state lives in beat config (`{project}/.git/beat-skip.json`).
  No scheduling fields in `.erg` files.
- **R4:** Triage notes are plain `note` log entries. No hash or expiry fields.
- **R5:** `Blocked-by:` encodes dependency; beat config encodes scheduling.
  Both are orthogonal to Status.

### Beat-config skip list

Scheduling state (cooldowns, scope-too-large flags, needs-human markers)
lives in `{project_dir}/.git/beat-skip.json` — machine-local, ephemeral, not
committed.

```json
{
  "version": 1,
  "entries": [
    { "id": "0028", "until": "2026-05-03T08:00Z", "reason": "scope-too-large" },
    { "id": "0041", "until": "2026-05-02T22:00Z", "reason": "cooldown-recent-pick" },
    { "id": "0055", "reason": "needs-human: milestone design needs user decision" }
  ]
}
```

`until` absent or null → skip indefinitely (use for needs-human cases).
Housekeeping sweeps expired entries on each run.

## Ready query

A ticket is **ready** (pickable) when:
- `Status: open`
- No local or remote branch name contains the ticket ID
- Every `Blocked-by` local ref points to a `Status: closed` ticket
- Not in the beat-config skip list with a future `until` timestamp

## Archive criteria

A ticket is **archivable** when:
- `Status: closed`
- Last log entry older than 90 days
- Not referenced by any live ticket's `Blocked-by` header (DAG safety)

Archive moves the file to `tickets/archive/` via `git mv`.

## Validator rules (pre-commit)

The Go validator enforces:
1. Magic first line is `%erg v1` (reject unknown versions)
2. All required headers present
3. No unknown headers
4. `Status` value is in the enum (`open`, `closed`)
5. `Created` is a valid ISO date (`YYYY-MM-DD`)
6. Filename matches `NNNN-{slug}.erg` pattern (4-digit ID, ASCII slug)
7. No duplicate IDs across `tickets/` and `tickets/archive/`
8. `Blocked-by` local refs point to existing ticket IDs
9. No dependency cycles
10. Log lines match `{timestamp} {actor} {verb}` format
11. Each separator (`--- log ---`, `--- body ---`) appears exactly once

## Relationship to GitHub Issues

| Concern | Tool |
|---------|------|
| Local work organization | `.erg` files |
| In-progress signal | branch names (contains ticket ID) |
| Cross-machine coordination | remote branches + `Blocked-by: gh#N` |
| Multi-agent coordination | GitHub Issues |
| Public visibility, review | GitHub Issues + PRs |

A ticket may reference a GitHub issue (`Blocked-by: gh#435`) but never
caches it. The two systems are independent.

## Postel's Law

**Strict on write, tolerant on read.** The validator enforces `%erg v1`
on commit. But you — the agent — are the parser for arbitrary input. If you
receive ticket-like information in any form (raw JSON from `gh`, a sentence,
a markdown sketch), understand the intent and write clean `%erg v1`. The
pre-commit hook catches mistakes. The tolerance is in you, not the tooling.
