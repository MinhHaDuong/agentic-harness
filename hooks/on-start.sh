#!/bin/bash
# SessionStart hook: set agent identity and activate git hooks.
# Runs at the beginning of every Claude Code session.

# Auto-update harness from ImperialDragonHarness repo (once per day)
_harness_stamp="$HOME/.claude/.last-pull"
_today=$(date +%Y-%m-%d)
if [ ! -f "$_harness_stamp" ] || [ "$(cat "$_harness_stamp")" != "$_today" ]; then
    git -C "$HOME/.claude" pull --ff-only --quiet 2>/dev/null && echo "$_today" > "$_harness_stamp"
fi

# Persist .env vars to CLAUDE_ENV_FILE (survives hook exit)
persist_env() {
    local envfile="$1"
    [ -f "$envfile" ] || return 0
    [ -n "$CLAUDE_ENV_FILE" ] || return 0
    grep -v '^\s*#' "$envfile" | grep -v '^\s*$' | sed 's/^export //' >> "$CLAUDE_ENV_FILE"
}

# User-level env loaded unconditionally (before project-dir check)
persist_env "$HOME/.claude/.env"

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
    export GH_TOKEN="$AGENT_GH_TOKEN"
fi

# Set agent identity
if [ -n "$AGENT_GIT_NAME" ]; then
    git config user.name "$AGENT_GIT_NAME"
fi
if [ -n "$AGENT_GIT_EMAIL" ]; then
    git config user.email "$AGENT_GIT_EMAIL"
fi

# Activate project hooks if hooks/ directory exists
if [ -d hooks ]; then
    git config core.hooksPath hooks 2>/dev/null
fi

echo "Agent identity configured."
if [ -f STATE.md ]; then
    cat STATE.md
fi
