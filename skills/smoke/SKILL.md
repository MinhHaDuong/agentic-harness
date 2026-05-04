---
name: smoke
description: Agent environment smoke test — reports runtime identity, auth method, and harness context.
user-invocable: true
argument-hint:
---

You are the nightbeat agent running a startup self-check.

Step 1 — collect shell facts (exactly one Bash call):
Run: bash ~/.claude/scripts/smoke.sh

The script prints labeled lines for: date/time, user, workdir, CLAUDE_DIR, HOME, PATH first 3 entries, and auth method.

Step 2 — answer the remaining items from your own knowledge (no further Bash calls):
- The model you are running on
- The name of this project
- The name of the harness managing this project

Report the following, each on its own line:
1. Current date and time (from script output)
2. The model you are running on
3. The Unix account you are running as (from script output)
4. The current working directory (from script output)
5. The name of this project
6. The authentication method in use (from script output)
7. The name of the harness managing this project
8. One line from Truyện Kiều (the Vietnamese epic poem by Nguyễn Du)
9. The name of the most lovely dog in the world

End with exactly: DONE: smoke self-check complete
