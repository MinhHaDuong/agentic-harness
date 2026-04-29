---
name: perch
description: Mid-session orientation — summarize what's done, surface unresolved points. Assesses clear-readiness and offers to do the work if conditions are right.
user-invocable: true
argument-hint:
---

# Perch — mid-session position check

## Steps

1. **Ground in git.** One Bash call: `git log --oneline --since="6am"; echo "---"; git status --short`. Name dirty files if any — do not diff them.

2. **Report: Done.** What is concretely finished in this conversation:
   - Files written or edited.
   - Commits and PRs merged.
   - Tickets closed.
   - Decisions reached.
   Items only. No prose.

3. **Report: Open.** Raised but not finished:
   - Work mentioned but not started or deferred.
   - Issues discovered but not fixed.
   - Docs or state noted as stale.
   - Questions asked and not answered.
   Items only. Be specific — a vague "follow-up needed" is useless.

4. **Report: Drift** (only if present). Topics that diverged from the original goal. Omit section entirely if there was no drift.

5. **One-line stance.** Where things stand and what the natural next move is.

6. **Assess clear-readiness.** After the report, silently evaluate:
   - Is this a natural reset point? (task complete, decision made, milestone reached)
   - Are Open items light enough to close out quickly? (ticket, memorize, or commit each one)
   - Is there uncommitted work that needs a commit first?

   **If conditions are favorable:** propose a clear offer — one sentence naming exactly what you will do (e.g. "I can ticket X, save memory Y, and commit Z, then we're clear to /clear"). Wait for yes.

   **If not favorable** (deep mid-task, many open threads, risky uncommitted state): say nothing. The report stands alone.

## Output shape

```
## Done
- …

## Open
- …

## Drift  ← omit if none
- …

**Stance:** [one sentence]

[Clear offer if conditions are right — else nothing]
```

No headers beyond these. No preamble. No "Here is a summary of…" opener.
