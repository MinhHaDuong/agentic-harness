#!/bin/bash
set -euo pipefail
# SessionStart hook: load env vars, enforce worktree isolation.
# Runs at the beginning of every Claude Code session.

# Persist .env vars to CLAUDE_ENV_FILE so Bash subprocesses (uv run, etc.) see them.
# Claude itself auto-loads .env, but child processes don't inherit its environment.
persist_env() {
    local envfile="$1"
    [ -f "$envfile" ] || return 0
    [ -n "${CLAUDE_ENV_FILE:-}" ] || return 0
    grep -v '^\s*#' "$envfile" | grep -v '^\s*$' | sed 's/^export //' >> "$CLAUDE_ENV_FILE" || true
}

# User-level env
persist_env "$HOME/.claude/.env"

# Worktree instruction — must always print, before any early exit
echo "Worktree isolation is enabled for this project. Every new conversation must start in its own worktree. Use EnterWorktree as your first action before responding to the user."

# Check for stale rules (advisory — prints warnings if any)
_script_dir="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$_script_dir/warn-stale-rules.sh" ]; then
    _stale=$(bash "$_script_dir/warn-stale-rules.sh" 2>/dev/null)
    [ -n "$_stale" ] && echo "$_stale"
fi

# Check shell-init.sh is sourced in the user's shell config
_shell_init="$HOME/.claude/scripts/shell-init.sh"
if ! grep -qlF "shell-init.sh" "$HOME/.bashrc" "$HOME/.zshrc" 2>/dev/null; then
    echo "SETUP REMINDER: shell-init.sh is not sourced in your shell config. Add this line to ~/.bashrc or ~/.zshrc:"
    echo "  [ -f \"$_shell_init\" ] && source \"$_shell_init\""
fi

# --- Nothing below this line may produce stdout (hook output = conversation context) ---
exec >/dev/null 2>&1

# Everything below requires a project directory
[ -n "${CLAUDE_PROJECT_DIR:-}" ] && cd "$CLAUDE_PROJECT_DIR" || exit 0

# Project-level env (skip if same as user-level to avoid duplication)
if [ "$(readlink -f "${CLAUDE_PROJECT_DIR:-}/.env" 2>/dev/null)" != "$(readlink -f "$HOME/.claude/.env" 2>/dev/null)" ]; then
    persist_env "$CLAUDE_PROJECT_DIR/.env"
fi

# Activate project git hooks if a pre-commit hook exists
if [ -f hooks/pre-commit ]; then
    git config core.hooksPath hooks
fi
