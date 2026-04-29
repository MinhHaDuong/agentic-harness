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

1. Run `erg ready --json tickets/` to list open, unblocked tickets with their
   cache status. Each JSON entry has:

   - `"cache":"skip"` — a prior `sweep-skip` log line with matching body hash;
     exclude this ticket from the beat without reading its body.
   - `"cache":"hit"` — body unchanged since last assessment; use the `scope`
     and `risk` fields from the JSON directly for ranking. Do not read the body.
   - `"cache":"miss"` — no valid cache; read the body and assess normally.

   The binary computes all hashes and compares them to log tokens — no hash
   computation in the skill.

2. **Exclude** (for cache:miss and cache:hit tickets — cache:skip already handled in step 1):
   - Tickets with status or tags: `needs-human`, `post-talk`, `post-conference`,
     `deferred`:
     `erg sweep-skip tickets/{file} status-{tag}`
   - Tickets whose `## Attempt log` has a `FAILED` or `BLOCKED` entry within
     the last 24 h (read body for this check):
     `erg sweep-skip tickets/{file} cooldown-24h expires:{failed-ts+24h}`
   - Tickets whose scope won't fit the 50-minute beat window (read body):
     `erg sweep-skip tickets/{file} scope-too-large expires:{now+24h}`
   - Tickets whose log contains a `sweep-pick: picked` entry less than 8 h old
     **and** whose `Status` is still `open` (orchestrator ran but did not close
     the ticket — re-picking immediately wastes a beat):
     `erg sweep-skip tickets/{file} cooldown-recent-pick expires:{pick-ts+8h}`

   Run `erg sweep-skip` before any further exclusion action so the cache entry
   is durable even if later steps fail. The binary computes the hash.

3. **3-strikes rule.** For any remaining ticket whose `## Attempt log` has
   3 or more entries: **append a sweep-skip log line** with reason
   `three-strikes` and no `expires:` token, then mark it `needs-human` in its
   front-matter, commit on the default branch, and exclude it from this run:
   `{ISO8601} claude note sweep-skip: three-strikes hash:{12hex}`

4. **Rank remaining candidates:**
   1. Tickets with `fix-tests` in their slug first
   2. Then by lowest risk — prefer tickets that touch few files, change
      docs/config/tests rather than core logic, and are easily reversible
      with no external dependencies
   3. If risk is equal, prefer the simpler one

   For each candidate (winner and runners-up), call:

   ```
   erg sweep-write tickets/{file} <picked|not-picked> "<scope>" "<risk>" "<reason>"
   ```

   The binary compares the current body hash against the stored log token.
   - Outputs `CACHED` → no write, no commit needed for this ticket.
   - Outputs `WROTE` → body assessment section + log line written in place.

   Collect which tickets output `WROTE`. If any, commit all modified ticket
   files in a single commit on the default branch before emitting output.
   If all output `CACHED`, skip the commit entirely.

5. If the candidate set is empty, output `IDLE: no eligible tickets` and stop.

## Output

Exactly one line:
- `PICK: <ticket-id>`
- `IDLE: no eligible tickets`
