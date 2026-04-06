#!/bin/bash
# PreToolUse hook: block destructive Bash commands.
# Exit 0 = allow, Exit 2 = deny with message.

# Read tool input from stdin (JSON with tool_input.command)
input=$(cat)

# Require jq — if missing, deny by default rather than silently allowing all
if ! command -v jq &>/dev/null; then
    echo "BLOCKED: jq not found — guard-destructive-bash.sh cannot parse tool input." >&2
    exit 2
fi

cmd=$(echo "$input" | jq -r '.tool_input.command // empty')
[ -z "$cmd" ] && exit 0

# Patterns that are destructive and hard to reverse

# rm -rf / rm -fr / rm --force (any combination)
if echo "$cmd" | grep -qE '\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|.*--force)\b'; then
    echo "BLOCKED: rm -rf/--force detected. Use targeted rm or move to trash instead." >&2
    exit 2
fi

if echo "$cmd" | grep -qE '\bgit\s+reset\s+--hard\b'; then
    echo "BLOCKED: git reset --hard destroys uncommitted work. Use git stash or git checkout <file> instead." >&2
    exit 2
fi

# git push --force / -f (but NOT --force-with-lease)
if echo "$cmd" | grep -qE '\bgit\s+push\s+.*--force($|\s)|\bgit\s+push\s+.*\s-f($|\s)'; then
    echo "BLOCKED: force push can destroy remote history. Use --force-with-lease if needed." >&2
    exit 2
fi

if echo "$cmd" | grep -qE '\bgit\s+clean\s+-[a-zA-Z]*f'; then
    echo "BLOCKED: git clean -f permanently deletes untracked files. Use git clean -n to preview first." >&2
    exit 2
fi

if echo "$cmd" | grep -qE '\bsudo\s+rm\b'; then
    echo "BLOCKED: sudo rm is too dangerous for automated execution. Run manually if needed." >&2
    exit 2
fi

if echo "$cmd" | grep -qEi '\bdrop\s+(table|database)\b'; then
    echo "BLOCKED: DROP TABLE/DATABASE detected. Run manually if intended." >&2
    exit 2
fi

exit 0
