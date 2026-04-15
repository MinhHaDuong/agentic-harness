#!/bin/bash
# SessionStart hook: set agent identity and activate git hooks.
# Runs at the beginning of every Claude Code session.

# Auto-update harness from ImperialDragonHarness repo (once per day)
_harness_stamp="$HOME/.claude/.last-pull"
_today=$(date +%Y-%m-%d)
if [ ! -f "$_harness_stamp" ] || [ "$(cat "$_harness_stamp")" != "$_today" ]; then
    git -C "$HOME/.claude" pull --ff-only --quiet 2>/dev/null && echo "$_today" > "$_harness_stamp"
fi

# Persist .env vars to CLAUDE_ENV_FILE (fresh each session, no dedup needed)
persist_env() {
    local envfile="$1"
    [ -f "$envfile" ] || return 0
    [ -n "$CLAUDE_ENV_FILE" ] || return 0
    grep -v '^\s*#' "$envfile" | grep -v '^\s*$' | sed 's/^export //' >> "$CLAUDE_ENV_FILE"
}

# User-level env loaded unconditionally (before project-dir check)
persist_env "$HOME/.claude/.env"

# Tell uv to load API keys automatically (no --env-file needed)
if [ -n "$CLAUDE_ENV_FILE" ] && [ -f "$HOME/.claude/.env" ]; then
    echo "UV_ENV_FILE=$HOME/.claude/.env" >> "$CLAUDE_ENV_FILE"
fi

# The worktree instruction must always print, regardless of project dir
echo "Worktree isolation is enabled for this project. Every new conversation must start in its own worktree. Use EnterWorktree as your first action before responding to the user."

# --- Nothing below this line may produce stdout (hook output = conversation context) ---
# Redirect stdout+stderr to /dev/null for the rest of the script
exec >/dev/null 2>&1

# Everything below requires a project directory
[ -n "$CLAUDE_PROJECT_DIR" ] && cd "$CLAUDE_PROJECT_DIR" || exit 0

persist_env "$CLAUDE_PROJECT_DIR/.env"    # project-level (overrides)

# Source persisted vars so they're available for git config below
if [ -n "$CLAUDE_ENV_FILE" ] && [ -f "$CLAUDE_ENV_FILE" ]; then
    set -a; source "$CLAUDE_ENV_FILE"; set +a
fi

# GH_TOKEN alias (gh CLI needs this specific name)
if [ -n "$AGENT_GH_TOKEN" ] && [ -n "$CLAUDE_ENV_FILE" ]; then
    echo "GH_TOKEN=$AGENT_GH_TOKEN" >> "$CLAUDE_ENV_FILE"
fi

# Activate project git hooks if a pre-commit hook exists
if [ -f hooks/pre-commit ]; then
    git config core.hooksPath hooks
fi

# Check for stale rules (advisory — output suppressed)
_script_dir="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$_script_dir/warn-stale-rules.sh" ]; then
    bash "$_script_dir/warn-stale-rules.sh"
fi
