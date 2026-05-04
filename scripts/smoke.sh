#!/bin/bash
set -euo pipefail
# smoke.sh — collect environment facts for the smoke skill
# Prints labeled output for shell-derivable items; LLM handles the rest.

DATE_TIME="$(date)"
USER_NAME="$(whoami)"
WORK_DIR="$(pwd)"
CLAUDE_DIR_VAL="${CLAUDE_DIR:-not set}"
HOME_VAL="${HOME:-not set}"
PATH_FIRST3="$(echo "$PATH" | tr ':' '\n' | head -3 | tr '\n' ':' | sed 's/:$//')"
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    AUTH_METHOD="API key (ANTHROPIC_API_KEY is set)"
else
    AUTH_METHOD="OAuth/Max account (ANTHROPIC_API_KEY not set)"
fi

echo "date/time:   $DATE_TIME"
echo "user:        $USER_NAME"
echo "workdir:     $WORK_DIR"
echo "CLAUDE_DIR:  $CLAUDE_DIR_VAL"
echo "HOME:        $HOME_VAL"
echo "PATH(first3): $PATH_FIRST3"
echo "auth:        $AUTH_METHOD"
