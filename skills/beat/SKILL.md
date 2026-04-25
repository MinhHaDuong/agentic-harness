---
name: beat
description: Trigger one beat cycle on the current project (housekeeping → pick-ticket → orchestrator).
user-invocable: true
argument-hint:
---

Run one beat cycle on the current project and report the outcome.

```bash
BEAT_PROJECT=$(pwd) python3 ~/.claude/scripts/beat.py
```

When it finishes, read the last line of `beat-log.jsonl` in the current project
and report: project, ticket_id, outcome, duration_s.
