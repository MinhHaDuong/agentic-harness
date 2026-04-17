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

## Checks

1. **Recent activity** — `git log --since="12 hours ago" --oneline --all` — summarize commit count and key themes
2. **Open PRs** — `gh pr list --state open` — list or confirm zero. Skip with reason if `gh` unavailable or no remote.
3. **Origin sync** — `git fetch origin` then compare `HEAD` vs `origin/<default-branch>` — report ahead/behind/synced. Skip if no `origin` remote.
4. **Branch hygiene** — `git branch -a` — list all, flag stale feature branches
5. **Worktrees** — `git worktree list` — list all, flag any orphaned worktrees beyond the current session
6. **Orphan commits** — `git fsck --unreachable --no-reflogs 2>&1 | grep "^unreachable commit"` — report count or "none"
7. **Working tree** — `git status --short` — report clean or list uncommitted changes
8. **Tests green** — run the project's test suite and report pass/fail. Entry-point autodetect:
   - If `Makefile` defines a `test` target → `make test`
   - Else if `pyproject.toml` exists → `uv run pytest` (or `pytest` if `uv` unavailable)
   - Else if `package.json` defines a `test` script → `npm test`
   - Else → skip with reason `no test entry point detected`

   Report: `N passed`, or `K failed / N total` plus the first failing test name. Slowest check; expect 10s–minutes.

9. **Docs freshness (deep verification)** — run `scripts/docs_freshness.sh` (bundled with this skill) to get the mechanical report, then perform the manual cross-checks below. This check **must not be shallow** — existence alone is not enough. Scan every canonical status/directive doc that exists at the repo root: `STATE.md`, `MASTERPLAN.md`, `README.md`, `ROADMAP.md`, `ARCHITECTURE.md`, and any other top-level `*.md` whose filename is all-caps or clearly a status/directive doc. Skip docs that don't exist; don't invent them.

   a. **Staleness timestamp.** `git log -1 --format=%ci -- <file>` — days since last commit touching the file. Warn if > 7 days have passed *and* the "Status"/"Last updated" line inside the doc predates the most recent repo activity. Fail if > 30 days with no update.

   b. **Ticket cross-check** (conditional on `tickets/*.erg` presence — git-erg in use). Extract every `0\d{3}` or `ticket 0\d{3}` reference in the doc. Partition by context: "done" (inside `[x]` checkbox, "Closed" section, "merged" phrase) vs "todo" (inside `[ ]` checkbox, "Next actions", "Open tickets", "pending"). For each ticket ID, read `tickets/0NNN-*.erg` `Status:` header. Flag mismatches:
      - Ticket listed as todo but `Status: closed` → stale TODO (most common drift)
      - Ticket listed as done but `Status: open` → premature claim
      - Referenced ticket ID not found in `tickets/` → broken ref

      If `tickets/*.erg` is absent, skip this sub-check with reason `no git-erg tickets detected`. The helper script automates the most common drift; always run it when tickets exist.

   c. **PR cross-check.** Extract every `#\d{3,}` reference. For each PR mentioned as pending / in-flight / open, verify via `gh pr view N --json state,title`. Flag merged PRs still described as pending work, and closed-without-merge PRs still described as landed. Skip if `gh` unavailable.

   d. **Count consistency.** If the doc contains a count like "Open tickets (N)" or "N open", cross-check N against `grep -l "^Status: open" tickets/*.erg | wc -l` (add `pending` count if included). Flag drift. Skip if tickets absent or no count pattern found.

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
| Orphan commits   | ...    | none / N found               |
| Working tree     | ...    | clean / N changes            |
| Tests green      | ...    | N passed / K failed          |
| Docs freshness   | ...    | N docs scanned, K stale refs |
```

Use `ok` for normal status, `warn` for attention-needed, `fail` for problems, `skip` for gracefully-degraded checks (detail column explains why).

If docs freshness is warn/fail, list each stale finding under the table as one bullet per finding, with the doc, line reference, and the fix (e.g., `STATE.md:39 — ticket 0095 listed as TODO but Status: closed (PR #259)`). This detail is the point of the deep check — do not compress it into a single line.

After the table (and any stale-findings list), add a one-line summary verdict.
