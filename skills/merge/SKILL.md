---
name: merge
description: Atomically close the linked ticket and squash-merge a PR. Must be run from the PR head branch. Works in git worktrees and on VMs. GitHub-only (requires the GitHub CLI).
user-invocable: true
argument-hint: [pr-number]
---

# Merge $ARGUMENTS

Run:
```bash
~/.claude/skills/merge/erg-pr-merge $ARGUMENTS
```

Report stdout/stderr verbatim. If the script exits non-zero, stop and show the error.
