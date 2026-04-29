---
name: housekeeping
description: Repo housekeeping — git sync, healthcheck, eager fix-now repairs, and ticket creation for open-ticket findings. Safe to call interactively or from automated sweeps.
user-invocable: true
argument-hint:
---

# Housekeeping

Run full repo housekeeping and act on every finding.

## Steps

1. **Git sync.** `git fetch --all --prune --quiet` then `git gc --auto`. Log if working tree is dirty (do not abort).

2. **Healthcheck.** Invoke /healthcheck. Parse the Action plan.

3. **Fix `fix-now` items.** Apply every `fix-now` item inline. If any fixes were
   applied, commit once: `chore: housekeeping fixes (sweep)`.

4. **Ticket `open-ticket` items.** For each `open-ticket` finding:
   - Search open ticket slugs and titles for key terms from the finding.
   - If no existing ticket covers it, create one with /ticket-new using a
     specific title. For test failures, the slug must contain `fix-tests`
     (e.g. `0042-fix-tests-module-not-found`).
   - If a ticket already exists, skip.

5. **Log `skip` items.** One line each, no action.

6. **Timestamp.** Update STATE.md to note the housekeeping run UTC date and time, commit it.

7. **Report.** Summarize what you did.
