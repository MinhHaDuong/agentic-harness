#!/bin/bash
# PostToolUse hook: run ruff on edited Python files.
# Feeds errors back to the agent so it can self-correct.

input=$(cat)

if ! command -v jq &>/dev/null; then
    exit 0  # non-blocking: lint is advisory, not a gate
fi

file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
[ -z "$file_path" ] && exit 0
[[ "$file_path" == *.py ]] || exit 0

# Run ruff check (fix safe violations) then format
if command -v uv &>/dev/null; then
    output=$(uv run ruff check --fix --quiet "$file_path" 2>&1)
    uv run ruff format --quiet "$file_path" 2>/dev/null
elif command -v ruff &>/dev/null; then
    output=$(ruff check --fix --quiet "$file_path" 2>&1)
    ruff format --quiet "$file_path" 2>/dev/null
else
    exit 0  # no linter available
fi

if [ -n "$output" ]; then
    echo "ruff: $output"
fi

exit 0
