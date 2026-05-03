#!/bin/bash
set -euo pipefail
# SessionStart hook: enforce worktree isolation.
# Runs at the beginning of every Claude Code session.
#
# NOTE: env vars (.env secrets) are injected into bash subprocesses via BASH_ENV
# (settings.json → env.BASH_ENV → scripts/bash-env.sh). Do NOT use CLAUDE_ENV_FILE
# for secrets: that mechanism inlines KEY=VALUE in argv, leaking to ps -ef.

# Worktree instruction — skip in automated night-sweep runs
if [[ -z "${CLAUDE_NIGHT_SWEEP:-}" ]]; then
    echo "Worktree isolation is enabled for this project. Every new conversation must start in its own worktree. Use EnterWorktree as your first action before responding to the user."
fi

echo "Running on host: $(hostname -s)"

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

# Inject the harness-rules index (pointers, not bodies). Agents read
# individual rule files on demand; verify-adherence checks ex post.
cat "$_script_dir/../skills/harness-rules/README.md" 2>/dev/null || true

# --- Nothing below this line may produce stdout (hook output = conversation context) ---
exec >/dev/null 2>&1

# Everything below requires a project directory
[ -n "${CLAUDE_PROJECT_DIR:-}" ] && cd "$CLAUDE_PROJECT_DIR" || exit 0

# Activate project git hooks if a pre-commit hook exists
if [ -f hooks/pre-commit ]; then
    git config core.hooksPath hooks
fi
