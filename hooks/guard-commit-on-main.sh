#!/bin/bash
# PreToolUse hook: block git commit on main/master branch.
# Enforces the "main is read-only" rule from git.md.

input=$(cat)

if ! command -v jq &>/dev/null; then
    echo "BLOCKED: jq not found — guard-commit-on-main.sh cannot parse tool input." >&2
    exit 2
fi

cmd=$(echo "$input" | jq -r '.tool_input.command // empty')
[ -z "$cmd" ] && exit 0

# Only check git commit commands
echo "$cmd" | grep -qE '\bgit\s+commit\b' || exit 0

# Get current branch
branch=$(git branch --show-current 2>/dev/null)

if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
    echo "BLOCKED: committing directly to $branch. Create a branch first: git switch -c <branch-name>" >&2
    exit 2
fi

exit 0
