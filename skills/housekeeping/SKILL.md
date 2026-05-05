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

1b. **DAG coherence check.** Run `erg check` if available (command tracked in
    git-erg/0038) to surface duplicate IDs, dangling Blocked-by refs, and
    folder-closure issues. Degrade gracefully if the command is not yet
    installed:
    ```bash
    ERG=${ERG:-tickets/tools/go/erg}
    $ERG check tickets/ 2>/dev/null || true
    ```
    Emit any output as housekeeping warnings; do not abort on non-zero exit.

2. **Healthcheck.** Invoke /healthcheck. The probe (`project-state.py`)
   runs once inside healthcheck and covers all checks — do not re-run git
   commands already collected there. Parse the **Action plan** section from
   the output: the bold headings `**fix-now**`, `**open-ticket**`, `**skip**`
   are the contract interface consumed by steps 3–5 below.

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
from the remote default branch. Behaviour stays the same — commit fix-now
items and the timestamp as usual. Do NOT push or open a PR yourself.
`beat.py` checks for commits after you exit: if there are none it deletes
the branch; if there are commits it leaves the branch locally as a
"deferred" candidate for human review.

If `BEAT_HOUSEKEEPING_BRANCH` is unset (interactive `/housekeeping`), commit
in place as before — no PR detour for hand-typed runs.
