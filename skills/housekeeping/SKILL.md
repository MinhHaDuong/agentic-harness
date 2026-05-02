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

1a. **Beat-skip sweep.** If `.git/beat-skip.json` exists, remove entries where
    `until` is present and `until < now`. Rewrite the file in place. This
    prevents the skip list from accumulating expired entries across beats.

1b. **Stale-branch check.** List local branches whose name contains a 4-digit
    ticket ID (`git branch --list`). For each, check if the ticket is already
    `closed` and the branch has no commits beyond `main` in the last 24 h.
    Report these as candidates for cleanup but do not auto-delete — list them
    in the housekeeping summary for human review.

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

## Beat mode

When `BEAT_HOUSEKEEPING_BRANCH` is set in the environment, you are running
under `beat.py` on a dedicated `claude/housekeeping-*` branch already cut
from `origin/main`. Behaviour stays the same — commit fix-now items and the
timestamp as usual. `beat.py` handles push, PR creation, CI verification,
and squash-merge once you exit; do NOT push or open a PR yourself. The
no-push guard is relaxed for that branch only.

If `BEAT_HOUSEKEEPING_BRANCH` is unset (interactive `/housekeeping`), commit
in place as before — no PR detour for hand-typed runs.
