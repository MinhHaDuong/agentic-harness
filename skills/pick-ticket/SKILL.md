---
name: pick-ticket
description: Pick the lowest-risk available ticket for an autonomous sweep run. Returns PICK:<id> or IDLE.
user-invocable: true
argument-hint:
---

# Sweep-pick

Select one ticket for the current sweep run.

## Steps

0. Resolve the `erg` binary once:
   ```bash
   ERG=$(command -v erg 2>/dev/null || echo "tickets/tools/go/erg")
   ```
   Use `$ERG` for every subsequent call. Never search for the binary again.

1. **Get candidates.** Run `$ERG ready --json tickets/` to list open, unblocked
   tickets with no active branch. Each JSON entry has `id`, `title`, `file`.

2. **Apply beat-skip list.** Load `.git/beat-skip.json` (skip if absent).
   Exclude any entry where:
   - `until` is present AND `until > now` (ISO UTC comparison)
   - `until` is absent (indefinite skip — typically `needs-human`)

   Log each excluded id and reason to beat output. Do not read ticket bodies
   for excluded tickets.

3. **Assess remaining candidates.** For each remaining ticket, read its body
   and assess scope and risk:
   - **Scope:** estimated time and files touched (e.g. `30m/3f`)
   - **Risk:** `low`, `medium`, or `high` — prefer tickets that touch few
     files, change docs/config/tests rather than core logic, are easily
     reversible, and have no external dependencies

   Exclude tickets whose scope won't fit the beat window (~50 min):
   write a beat-skip entry `{ "id": "...", "until": "{now+24h}", "reason": "scope-too-large: ..." }`

   Exclude tickets whose log shows a `FAILED` or `BLOCKED` attempt within 24 h:
   write a beat-skip entry `{ "id": "...", "until": "{failed-ts+24h}", "reason": "cooldown-24h" }`

   If a ticket has been attempted 3 or more times without success:
   write a beat-skip entry `{ "id": "...", "reason": "three-strikes: needs human review" }` (no `until`)

4. **Rank remaining candidates:**
   1. Tickets with `fix-tests` in their slug first
   2. Then by lowest risk
   3. If risk is equal, prefer the simpler one

5. **Write beat-skip updates.** If any exclusions were computed in step 3,
   write them to `.git/beat-skip.json` now (merge with existing entries,
   replacing any entry with the same `id`). No ticket files are modified.
   No commit needed — beat-skip is machine-local state.

   For the picked ticket, if it was recently picked (log has a pick within 8 h
   and ticket is still open), add a cooldown entry:
   `{ "id": "...", "until": "{pick-ts+8h}", "reason": "cooldown-recent-pick" }`

6. If the candidate set is empty after all exclusions, output
   `IDLE: no eligible tickets` and stop.

## Output

Exactly one line:
- `PICK: <ticket-id>`
- `IDLE: no eligible tickets`

## Cross-worktree concurrency

Two concurrent sweeps may pick the same ticket; they diverge onto different
branches and the merge sorts it out. Cost: one wasted branch. Frequency: low
(two sweeps within seconds). Do not reintroduce a local lockfile or any
equivalent — that mechanism was removed upstream (git-erg 0013) and its
problems travel with the mechanism, not its location.
