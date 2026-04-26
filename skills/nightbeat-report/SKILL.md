---
name: nightbeat-report
description: Morning review of autonomous nightbeat runs. Parses logs, narrates work done, and surfaces harness improvement opportunities.
user-invocable: true
argument-hint: "[--hours N]"
---

# Nightbeat Report — morning review

Run this skill at the start of the day to review what the autonomous agent did overnight.

## Step 1 — Collect the raw report

Run the parser:

```bash
python3 ~/.claude/scripts/nightbeat-report.py --full
```

If you want a different window, accept `--hours N` passed as an argument and append it:

```bash
python3 ~/.claude/scripts/nightbeat-report.py --full --hours N
```

Read the output carefully. It contains four sections: run table, orchestrator results, warnings/issues, totals, and per-project summary.

## Step 2 — Narrate completed work

For each project that had at least one `done` outcome, write one paragraph summarising:

- Which tickets were worked and what was accomplished (draw from the orchestrator result texts)
- Whether any tickets were closed or remain open (look for "ticket closed", "status: closed")
- Branches ready for push/PR (look for "push blocked by night-sweep guard" or "git push" in the result text)

Keep it factual and brief. If the orchestrator result is ambiguous or incomplete, say so.

## Step 3 — Action items for the user

List concrete things requiring human action:

- **Branches to push**: every branch the agent mentions as blocked-by-guard is ready for a PR — name the branch and the project
- **Questions left open**: if the orchestrator result ends with a question or asks for a choice (e.g. "Option A / Option B"), flag it — the next session will stall without a decision
- **Failed tickets**: orchestrator `outcome=failed` — note the ticket, project, and cost spent

Format as a numbered checklist.

## Step 4 — Surface harness improvement opportunities

Examine the report for recurring patterns that indicate friction in the harness. For each pattern found, identify the root cause and propose a concrete fix:

**Permission denials**
If the same tool (e.g. `Bash`, `Edit`) appears repeatedly in the `denied:` column across multiple runs or projects:
- Identify the specific command being blocked (you may need to scan the log file for `permission_denials` near that run's timestamp)
- Propose adding it to the allowed list in `~/.claude/settings.json` under the relevant hook

**Housekeeping budget exhaustion**
If `hk:error_max_budget_usd` appears on multiple runs: the $0.25 housekeeping budget is chronically too tight. Propose raising `BUDGET_HOUSEKEEPING` in `beat.py` and note the observed cost.

**Housekeeping rc=1 without budget exhaustion**
A non-zero exit from housekeeping that isn't budget-related means the skill itself failed. Look at the log for that run to identify the cause. Propose a concrete fix or a ticket.

**Same ticket worked multiple times without closing**
If the same ticket ID appears in multiple runs for the same project: the ticket's exit criteria may be underspecified, or the orchestrator is not committing/closing. Propose reviewing the ticket's exit criteria or adding a stricter close step.

**Orchestrator asking questions**
If any orchestrator result ends with a question or multi-option choice, the ticket lacked sufficient specification. Propose adding the missing context to the ticket or to a project-level directive.

**Projects consistently idle**
If a project shows `idle` for every run in the window, its ticket backlog is empty. Note it — the user needs to add tickets or the project can be removed from the beat rotation temporarily.

**High costs with low output**
If a run spent > $3 on a ticket that is still not closed: flag the ticket for human review — it may be stuck in a loop or working on something underspecified.

Format this section as a bulleted list. If no patterns are found, say so explicitly — "No harness friction detected."

## Step 5 — Summary line

End with a one-line verdict:

```
Night: {N} runs, ${X.XX} spent — {K} tickets worked, {J} branches ready to push, {M} issues.
```
