---
name: beat
description: Trigger one beat cycle — runs beat.py (housekeeping → pick-ticket → orchestrator) on the next project in rotation.
user-invocable: true
argument-hint:
---

Run one beat cycle and report the outcome.

```bash
python3 ~/.claude/scripts/beat.py
```

When it finishes, read the last line of the relevant project's `beat-log.jsonl`
and report: project, ticket_id, outcome, duration_s.
