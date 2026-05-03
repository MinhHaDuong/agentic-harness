---
name: pick-ticket
description: Pick the lowest-risk available ticket for an autonomous sweep run. Returns PICK:<id>, CLOSED:<id>, or IDLE.
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

   Exclude tickets whose body contains a `## Attempt log` section with a
   `FAILED` or `BLOCKED` entry dated within the last 24 h (read the body,
   find the most recent failure timestamp):
   write a beat-skip entry `{ "id": "...", "until": "{failed-ts+24h}", "reason": "cooldown-24h" }`

   If the `## Attempt log` section has 3 or more entries regardless of outcome:
   write a beat-skip entry `{ "id": "...", "reason": "three-strikes: needs human review" }` (no `until`)

4. **Lightweight exit-criteria check (Tier 2 of ticket 0049).** For each
   remaining candidate, check whether its exit criteria are *already* met
   in the codebase. The point: don't burn a ~$5 raid on a ticket whose
   work is already done (e.g. fixed as a side effect of another ticket).

   **Trigger gate** — only run this check on a candidate when *either*:
   - the ticket's `cache` field is `miss` in `erg ready --json` (body
     changed since last sweep), *or*
   - `git log --since=<last-pick-ts> -- <relevant-files>` returns matches
     (recent commits touched files the ticket talks about). Use the
     timestamp of the most recent `sweep-pick:` or `sweep-close:` log
     line in the ticket as `<last-pick-ts>`; if none, default to 7 days
     ago.

   Skip the check on cache-hit tickets with no recent relevant commits —
   nothing about them has changed, the answer is still "open."

   **Allowed checks** — only consider exit criteria expressible as one of
   these three crisp grep-able shapes. Vague exits ("works correctly",
   "no regressions", "user-friendly") → leave open, do not attempt.

   1. **String absence**: `! grep -F "<literal>" <file>` — exit criterion
      reads "string X does not appear in file F."
   2. **File absence**: `test ! -f <path>` — exit criterion reads
      "file F does not exist."
   3. **Symbol presence**: `grep -E '^(def|class|func) <name>' <file>` —
      exit criterion reads "function/class/func `name` is defined in F."

   If *all* of a ticket's exit criteria reduce to these checks AND all
   pass:

   1. Compute the body hash: `bodyhash=$(${ERG} ready --json tickets/ \
      | jq -r '.[] | select(.id=="<id>") | .hash')`
   2. Call `/ticket-close <id>` (no reason argument — the close skill
      records the status change; the sweep-close note records why).
   3. Append a sweep-close log line to `tickets/<id>-*.erg` immediately
      below the most recent log entry, before `--- body ---`:
      `{now-iso} claude note sweep-close: already-done hash:<bodyhash>`
      Use UTC minute precision: `date -u +%Y-%m-%dT%H:%MZ`.
   4. Output `CLOSED: <id>` and stop processing this candidate (do not
      rank it). beat.py will loop back and pick again.

   If *any* exit criterion is vague or fails its check → leave the
   candidate open and proceed to ranking.

   Process candidates one at a time. The first `CLOSED:` is sufficient —
   beat.py loops on it. Do not batch-close multiple tickets in one run.

5. **Rank remaining candidates:**
   1. Tickets with `fix-tests` in their slug first
   2. Then by lowest risk
   3. If risk is equal, prefer the simpler one

6. **Write beat-skip updates.** Merge all new skip entries (from step 3) plus
   a cooldown entry for the picked ticket into `.git/beat-skip.json`,
   replacing any existing entry with the same `id`. No ticket files are
   modified. No commit needed — beat-skip is machine-local state.

   Always add a cooldown entry for the picked ticket (prevents re-picking on
   the next beat before the raid has a chance to close it):
   `{ "id": "...", "until": "{now+8h}", "reason": "cooldown-recent-pick" }`

7. If the candidate set is empty after all exclusions, output
   `IDLE: no eligible tickets` and stop.

## Output

Exactly one line:
- `PICK: <ticket-id>` — picked a ticket; raid will run.
- `CLOSED: <ticket-id>` — closed an already-done ticket; beat.py loops
  back to pick again. Bounded at 3 consecutive CLOSEDs per beat.
- `IDLE: no eligible tickets`

## Cross-worktree concurrency

Two concurrent sweeps may pick the same ticket; they diverge onto different
branches and the merge sorts it out. Cost: one wasted branch. Frequency: low
(two sweeps within seconds). Do not reintroduce a local lockfile or any
equivalent — that mechanism was removed upstream (git-erg 0013) and its
problems travel with the mechanism, not its location.
