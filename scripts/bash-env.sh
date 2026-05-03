#!/bin/bash
# Loaded via BASH_ENV — sourced at startup of every Claude Code bash subprocess.
# Exports .env secrets into the process environment without inlining them in argv
# (inlining in argv leaks secrets to ps -ef, which is visible to all local users).
#
# BASH_ENV is honored by non-interactive bash (i.e. "bash -c ..."), which is
# exactly what Claude Code uses for Bash tool calls.

set -a  # mark all subsequent assignments for export

[ -f "$HOME/.claude/.env" ] && source "$HOME/.claude/.env"

# Project-level .env, identified by PWD (Claude Code sets PWD to the project dir
# for each subprocess). Skip if it resolves to the same file as the user-level one.
if [ -n "${PWD:-}" ] && [ -f "$PWD/.env" ]; then
    _be_proj="$(realpath "$PWD/.env" 2>/dev/null)"
    _be_user="$(realpath "$HOME/.claude/.env" 2>/dev/null)"
    [ "$_be_proj" != "$_be_user" ] && source "$PWD/.env"
    unset _be_proj _be_user
fi

set +a
