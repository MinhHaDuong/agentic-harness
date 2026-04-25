---
name: pick-ticket
description: Pick the lowest-risk available ticket for an autonomous sweep run. Reads attempt history from ticket bodies. Returns PICK:<id> or IDLE.
user-invocable: true
argument-hint:
---

# Sweep-pick

Select one ticket for the current sweep run.
Attempt history is read directly from each ticket's `## Attempt log` section.

## Steps

1. Run /ticket-ready to list open, unblocked tickets.

2. **Exclude:**
   - Tickets with status or tags: `needs-human`, `post-talk`, `post-conference`, `deferred`
   - Tickets whose `## Attempt log` contains a `FAILED` or `BLOCKED` entry
     dated within the last 24 hours
   - Tickets whose description indicates a compute job, model run, or batch execution
     (e.g. "run scripts on padme", "launch ablation", "rerun experiments") — these
     require human setup or a long-running detached process that a beat cannot provide

3. **3-strikes rule.** For any remaining ticket whose `## Attempt log` has
   3 or more entries: mark it `needs-human` in its front-matter, commit on
   the default branch, and exclude it from this run.

4. **Rank remaining candidates:**
   1. Tickets with `fix-tests` in their slug first
   2. Then by lowest risk — prefer tickets that touch few files, change
      docs/config/tests rather than core logic, and are easily reversible
      with no external dependencies
   3. If risk is equal, prefer the simpler one

5. If the candidate set is empty, output `IDLE: no eligible tickets` and stop.

## Output

Exactly one line:
- `PICK: <ticket-id>`
- `IDLE: no eligible tickets`
