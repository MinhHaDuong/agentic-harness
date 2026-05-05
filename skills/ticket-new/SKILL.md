---
name: ticket-new
description: Create a local %erg v1 file for agent coordination.
# Model-invocable: parses free-form input (title, sentence, JSON blob, paste) into %erg v1.
# Side effects are file-only — no branch, no PR — so autonomous capture is safe.
# Contrast start-ticket (disable-model-invocation: true), which creates worktree + branch + PR.
disable-model-invocation: false
user-invocable: true
argument-hint: [title]
---

# Create local ticket

**Input:** anything — a title, a sentence, a JSON blob from `gh`, a paste
from a conversation. Extract the intent and normalize to `%erg v1`.

## Steps

1. Determine the next ID:
   ```bash
   ERG=${ERG:-bin/erg}
   $ERG next-id tickets/
   ```
   Always use `erg next-id` — never compute or guess the ID manually.

2. Choose a slug: lowercase kebab-case, ASCII only (`[a-z0-9-]`), derived from the title.

3. Create `tickets/{ID}-{slug}.erg` with this exact structure:
   ```
   %erg v1
   Title: {imperative title}
   Created: {YYYY-MM-DD}
   Author: {agent or user}

   --- log ---
   {YYYY-MM-DD}T{HH:MM}Z {author} created

   --- body ---
   ## Context
   {why this work exists}

   ## Actions
   1. {concrete step}

   ## Test
   {first test to write — TDD red step}

   ## Exit criteria
   {definition of done}
   ```
   Note: no `Status:` header — `erg validate` rejects it.

4. Validate the new ticket (pass the specific file, not the directory):
   ```bash
   $ERG validate tickets/<new-file>.erg
   ```
   Fix any errors before committing.

5. Check blocker references (requires ticket 0035):
   ```bash
   $ERG verify-blockers tickets/ 2>/dev/null && echo OK || echo "WARNING: dangling Blocked-by refs — fix before committing"
   ```
   Skip gracefully if the command does not exist yet.

6. Commit the ticket file.

Format spec: `tickets/FORMAT.md` (or global rule `tickets.md`).
