---
name: healthcheck
description: Repo healthcheck — git hygiene, test status, and deep freshness verification of status/directive docs. Gracefully degrades when project-specific conventions (git-erg tickets, STATE.md, etc.) are absent.
disable-model-invocation: false
user-invocable: true
argument-hint:
---

# Repo healthcheck

Run a healthcheck on the current repository. Report results concisely — one line per check, flag anything abnormal.

This skill is user-level and must **gracefully degrade**: each check runs only if its prerequisites are present. Missing prerequisites yield a `skip` status with a one-line reason, never a fail.

## Data collection

First, run the mechanical probe to collect structured state:

```bash
python3 ~/.claude/scripts/project-state.py "$(git rev-parse --show-toplevel)" --full
```

Parse the JSON output. Use its fields to populate checks 1–7 below without re-running git commands. If the script is missing or fails, fall back to ad-hoc commands per check.

## Checks

1. **Recent activity** — commits in the last 12 hours, key themes (use `git log --since`)
2. **Open PRs** — from `prs.open` / `prs.items`. Skip if `prs.error`.
3. **Origin sync** — from `git.ahead` / `git.behind`. Skip if no remote.
4. **Branch hygiene** — list all, flag stale feature branches
5. **Worktrees** — list all, flag orphaned ones
6. **Working tree** — from `git.clean`. List uncommitted if dirty.
7. **Tests green** — from `tests.status` / `tests.detail`. Skip if `tests.runner == "none"`.
8. **Docs freshness (deep verification)** — cross-check status/directive docs (`STATE.md`, `README.md`, etc.):
   - **Staleness** — flag docs whose content predates recent repo activity
   - **Ticket cross-check** — references to tickets whose status contradicts
     the doc (todo but closed, done but open, broken ref). Skip if no `.erg` tickets.
     (Use `tickets.ready_ids` for the initial ticket list; only read specific tickets
     whose status contradicts a doc reference.)
   - **PR cross-check** — PRs described as pending but already merged/closed.
     Use `prs.items` from the probe. Skip if `prs.error`.
   - **Count consistency** — "N open tickets" claims vs `tickets.open` from probe

## Output format

```
## Healthcheck — {date}

| Check            | Status | Detail                       |
|------------------|--------|------------------------------|
| Recent activity  | ...    | N commits (last 12h)         |
| Open PRs         | ...    | N open                       |
| Origin sync      | ...    | synced / ahead N / ...       |
| Branch hygiene   | ...    | N local, N remote            |
| Worktrees        | ...    | N active                     |
| Working tree     | ...    | clean / N changes            |
| Tests green      | ...    | N passed / K failed          |
| Docs freshness   | ...    | N docs scanned, K stale refs |
```

Use `ok` for normal status, `warn` for attention-needed, `fail` for problems, `skip` for gracefully-degraded checks (detail column explains why).

If docs freshness is warn/fail, list each stale finding under the table as one bullet per finding, with the doc, line reference, and the fix (e.g., `STATE.md:39 — ticket 0095 listed as TODO but Status: closed (PR #259)`). This detail is the point of the deep check — do not compress it into a single line.

After the table (and any stale-findings list), add a one-line summary verdict.

## Action plan

After the verdict, if any findings are warn or fail, emit an **Action plan** section.
Classify every finding into exactly one of three categories:

- `fix-now` — trivial, no branch needed, reversible, no design decision: do it in the
  current session immediately after the user says "do it"
- `open-ticket` — multi-file, needs a branch, requires a design decision, or worth
  tracking across sessions: create a ticket
- `skip` — cosmetic, already tracked elsewhere, or not worth acting on now: note why

Format:

```
## Action plan

**fix-now**
- {one-line description of fix}

**open-ticket**
- {title} — {one-line reason it needs a ticket}

**skip**
- {finding} — {reason}
```

Omit a heading if it has no entries. If all checks are `ok`, omit the Action plan entirely.

Once the Action plan is fully effected, propose: "Surface remaining nits?"
