---
name: beat
description: Trigger one beat cycle on the current project (housekeeping → pick-ticket → raid).
user-invocable: true
argument-hint:
---

Run one beat cycle on the current project and report the outcome.

```bash
BEAT_PROJECT=$(git rev-parse --show-toplevel) python3 ~/.claude/scripts/beat.py
```

Report the one-line summary printed to stdout by beat.py.
