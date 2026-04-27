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

   The /ticket-ready output provides ticket IDs and titles without loading full
   file contents. Only read individual ticket files when needed for sweep-skip
   hash verification or scope assessment.

**Step 1.5 — Fast-path via sweep-skip cache**

Before reading any ticket body or estimating scope, scan each candidate's
`--- log ---` section for the most recent line matching `note sweep-skip:`.
Parse two optional tokens on that line:

- `expires:{ISO8601}` — if absent, treat as defer-until-human (no expiry)
- `hash:{12hex}` — SHA-256 of the `--- body ---` section content, first 12
  hex chars

To compute the body hash: take all bytes from the first character after the
`--- body ---` separator's terminating newline up to (but not including) the
first `## Picker assessment` line, raw UTF-8, SHA-256, first 12 hex chars.
This makes the hash stable across repeated picker runs that append assessments.
Example (no prior assessment):
`python3 -c "import hashlib,sys; d=open('tickets/NNNN-slug.erg','rb').read(); body=d.split(b'--- body ---\n',1)[1]; core=body.split(b'\n## Picker assessment',1)[0]; print(hashlib.sha256(core).hexdigest()[:12])"`

Skip re-assessment (and skip the ticket entirely this beat) if ALL hold:

- No `expires:` token, OR `expires:` value is strictly in the future
- The current body hash matches the `hash:` token

If the skip fires, do not write a new log line. Most-recent matching line wins.
If the skip does not fire (expired, hash mismatch, or no line), proceed with
full assessment below.

2. **Exclude:**
   - Tickets with status or tags: `needs-human`, `post-talk`, `post-conference`,
     `deferred` — **before excluding, append a sweep-skip log line** with
     reason `status-{tag}` (e.g. `status-needs-human`, `status-post-talk`) and
     no `expires:` token (defer-until-human):
     `{ISO8601} claude note sweep-skip: status-{tag} hash:{12hex}`
   - Tickets whose `## Attempt log` contains a `FAILED` or `BLOCKED` entry
     dated within the last 24 hours — **before excluding, append a sweep-skip
     log line** with reason `cooldown-24h` and `expires:` set to the
     failed/blocked timestamp + 24h:
     `{ISO8601} claude note sweep-skip: cooldown-24h expires:{failed-ts+24h} hash:{12hex}`
   - Tickets whose description indicates work that cannot fit in the 50-minute beat
     window — read the scope and estimate honestly; if completing the ticket would
     require hours (model runs, batch jobs, large refactors), skip it this beat —
     **before excluding, append a sweep-skip log line** with reason
     `scope-too-large` and `expires:` set to now + 24h:
     `{ISO8601} claude note sweep-skip: scope-too-large expires:{now+24h} hash:{12hex}`

   Write the sweep-skip log line before any subsequent exclusion action so the
   cache entry is durable even if later steps fail.

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

   After ranking, **write into every candidate ticket** (both winner and
   runners-up):

   1. Append a `## Picker assessment {ISO8601}` section to the ticket body
      in markdown. Include: decision (picked / not picked), scope estimate,
      risk level, one-line reason. Example:

      ```markdown
      ## Picker assessment 2026-04-26T15:30Z
      **Decision:** not picked
      **Scope:** ~30 min, 4 files
      **Risk:** low
      **Reason:** ticket 0042 was riper — plan already complete, fewer files
      ```

   2. Add a one-word log line as a pointer:
      - Runner-up: `{ISO8601} claude note sweep-assess: not picked`
      - Winner:    `{ISO8601} claude note sweep-pick: selected`

   Commit all body appends + log lines (candidates + any sweep-skip lines from
   steps 2–3) in a single commit on the default branch before emitting output.

   **On the next beat**, before full re-assessment of a candidate, check
   whether its most recent `## Picker assessment` section exists and its
   body hash (computed excluding prior assessments — see Step 1.5) still
   matches. If it does, reuse the scope and risk from that section and skip
   re-reading the body.

5. If the candidate set is empty, output `IDLE: no eligible tickets` and stop.

## Output

Exactly one line:
- `PICK: <ticket-id>`
- `IDLE: no eligible tickets`
