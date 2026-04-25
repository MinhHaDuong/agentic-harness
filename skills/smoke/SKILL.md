---
name: smoke
description: Agent environment smoke test — reports runtime identity, auth method, and harness context.
user-invocable: true
argument-hint:
---

You are the nightbeat agent running a startup self-check.

Use Bash to answer items 1, 3, 4, and 6 — do not guess them.

Report the following, each on its own line:
1. Current date and time (run: date)
2. The model you are running on
3. The Unix account you are running as (run: whoami)
4. The current working directory (run: pwd)
5. The name of this project
6. The authentication method in use — check: if ANTHROPIC_API_KEY is set, it is API key; otherwise OAuth/Max account (run: printenv ANTHROPIC_API_KEY || echo "not set")
7. The name of the harness managing this project
8. One line from Truyện Kiều (the Vietnamese epic poem by Nguyễn Du)
9. The name of the most lovely dog in the world

End with exactly: DONE: smoke self-check complete
