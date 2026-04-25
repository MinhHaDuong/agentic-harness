#!/bin/bash
# Launcher for the /beat skill. Rotates through projects hourly, 22:00–06:00.
#
# Auth: OAuth via ~/.claude/.credentials.json (Max account).
# Logs: ~/.claude/logs/nightbeat/ — text headers + stream-json from claude.
#       Extract cost: grep '"type":"result"' <logfile> | jq '.total_cost_usd'
set -euo pipefail

HARNESS_DIR="$HOME/.claude"
PROJECTS_ROOT="$HOME"

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

# Git author identity for commits by the agent
export GIT_AUTHOR_NAME="claude-agent"
export GIT_AUTHOR_EMAIL="claude-agent@localhost"
export GIT_COMMITTER_NAME="claude-agent"
export GIT_COMMITTER_EMAIL="claude-agent@localhost"

# Override SKILL env var to use a different entry point (e.g. /smoke)
SKILL="${SKILL:-/beat}"

# ERR trap: write a tombstone on any unexpected failure
trap 'echo "=== $SKILL ABORT rc=$? line $LINENO $(date -u +%FT%TZ) ===" >&2' ERR

# ── Lock: skip if a previous run hasn't finished ─────────────────────────────
# fd 200 is released on exit, unlocking automatically
LOCKFILE="${RUNTIME_DIRECTORY:-${XDG_RUNTIME_DIR:-$HOME/.cache}}/nightbeat.lock"
exec 200>"$LOCKFILE"
flock -n 200 || { echo "$(date -u +%FT%TZ): another $SKILL run still running, skipping." >&2; exit 0; }

# ── Logging ──────────────────────────────────────────────────────────────────
LOGDIR="$HARNESS_DIR/logs/nightbeat"
mkdir -p "$LOGDIR"
LOGFILE="$LOGDIR/$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "$LOGFILE") 2>&1
# Close fd 1 on exit so tee gets EOF and flushes; wait ensures no truncation
trap 'exec 1>&- 2>&-; wait 2>/dev/null || true' EXIT

# Keep the last 60 log files (≈ one week of nightly runs)
find "$LOGDIR" -name "*.log" -type f | sort -r | tail -n +61 | xargs -r rm -f 2>/dev/null || true

echo "=== $SKILL start $(date -u +%FT%TZ) ==="

# ── Project rotation (sequential counter, even coverage) ─────────────────────
PROJECTS=(
    "$PROJECTS_ROOT/aedist-technical-report"
    "$PROJECTS_ROOT/cadens"
    "$PROJECTS_ROOT/Climate_finance"
    "$PROJECTS_ROOT/fuzzy-corpus"
)

COUNTER_FILE="$LOGDIR/.run-counter"
COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
IDX=$(( COUNT % ${#PROJECTS[@]} ))
echo $(( COUNT + 1 )) > "$COUNTER_FILE"

# Guard against array shrink under set -u
(( IDX < ${#PROJECTS[@]} )) || { echo "ERROR: slot $IDX out of range (${#PROJECTS[@]} projects)"; exit 1; }

export PROJECT="${PROJECTS[$IDX]}"
echo "Run $COUNT  →  project slot $IDX: $PROJECT"

if [[ ! -d "$PROJECT/.git" ]]; then
    echo "ERROR: $PROJECT is not a git repository. Aborting."
    exit 1
fi

cd "$PROJECT"

# ── State directory bootstrap ────────────────────────────────────────────────
mkdir -p "$PROJECT/.claude/sweep-state"

# ── Run Claude ────────────────────────────────────────────────────────────────
BEAT_START=$(date +%s)

# SIGTERM trap: systemd TimeoutStartSec fires this; write a timeout spin-down
# before the process tree is killed so beat-log.jsonl doesn't stay in_progress.
_on_sigterm() {
    local elapsed=$(( $(date +%s) - BEAT_START ))
    local record
    record=$(jq -cn \
        --arg t "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --argjson d "$elapsed" \
        '{"last_run_at":$t,"ticket_id":null,"branch":null,"PR":null,
          "outcome":"aborted","diagnostics":"systemd SIGTERM — beat exceeded time budget",
          "duration_s":$d}') || true
    [[ -n "$record" ]] && printf '%s\n' "$record" >> "$PROJECT/beat-log.jsonl" 2>/dev/null || true
    echo "=== $SKILL SIGTERM elapsed=${elapsed}s $(date -u +%FT%TZ) ===" >&2
    exit 143
}
trap '_on_sigterm' TERM

# Guard: SIGKILL recovery — if last record is in_progress and < 55 min old,
# previous run was killed before it could write spin-down.
if [[ -s "$PROJECT/beat-log.jsonl" ]]; then
    _last=$(jq -s 'last' "$PROJECT/beat-log.jsonl")
    _out=$(printf '%s' "$_last" | jq -r '.outcome // ""')
    if [[ "$_out" == "in_progress" ]]; then
        _last_at=$(printf '%s' "$_last" | jq -r '.last_run_at // "1970-01-01T00:00:00Z"')
        _last_epoch=$(date -d "$_last_at" +%s 2>/dev/null || echo 0)
        if (( $(date +%s) - _last_epoch < 3300 )); then
            printf '%s\n' "$(jq -cn --arg t "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
                '{"last_run_at":$t,"ticket_id":null,"branch":null,"PR":null,
                  "outcome":"aborted","diagnostics":"crash/SIGKILL recovery — previous run never completed spin-down"}')" \
                >> "$PROJECT/beat-log.jsonl"
            echo "=== $SKILL aborted: crash recovery $(date -u +%FT%TZ) ===" >&2
            exit 0
        fi
    fi
fi
# Spin-in: launcher writes in_progress with a shell timestamp (not delegated to agent)
printf '%s\n' "$(jq -cn --arg t "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{"outcome":"in_progress","last_run_at":$t}')" >> "$PROJECT/beat-log.jsonl"

# --permission-mode bypassPermissions  non-interactive unattended mode
# --output-format stream-json          structured output; cost in .usage field
# --no-session-persistence             no writes to harness session store
# --settings                           destructive-bash + no-push guards
# --add-dir                            load CLAUDE.md from harness and project
# CLAUDE_NIGHT_SWEEP=1 tells on-start.sh to skip the worktree isolation message
# timeout 52m: primary soft kill — fires before systemd TimeoutStartSec=3420 (57 min);
#   beat.sh continues after claude exits and writes the aborted record cleanly.
#   Beat skill 55-min in-progress guard is the next layer; systemd is the hard last resort.
CLAUDE_RC=0
timeout 52m claude \
    --print \
    --verbose \
    --output-format stream-json \
    --permission-mode bypassPermissions \
    --no-session-persistence \
    --max-budget-usd 1.00 \
    --model sonnet \
    --settings "$HARNESS_DIR/scripts/beat-settings.json" \
    --add-dir "$HARNESS_DIR" \
    --add-dir . \
    -p "$SKILL" || CLAUDE_RC=$?

BEAT_ELAPSED=$(( $(date +%s) - BEAT_START ))

if [[ "$CLAUDE_RC" -eq 124 ]]; then
    # bash timeout fired: claude ran over the soft limit; write aborted record with duration
    record=$(jq -cn \
        --arg t "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --argjson d "$BEAT_ELAPSED" \
        '{"last_run_at":$t,"ticket_id":null,"branch":null,"PR":null,"outcome":"aborted","diagnostics":"bash timeout — claude exceeded 52-minute soft limit","duration_s":$d}') || true
    [[ -n "$record" ]] && printf '%s\n' "$record" >> "$PROJECT/beat-log.jsonl" 2>/dev/null || true
    echo "=== $SKILL timeout rc=124 elapsed=${BEAT_ELAPSED}s $(date -u +%FT%TZ) ===" >&2
elif [[ "$CLAUDE_RC" -ne 0 ]]; then
    echo "=== $SKILL claude exit rc=$CLAUDE_RC elapsed=${BEAT_ELAPSED}s $(date -u +%FT%TZ) ===" >&2
else
    # Clean exit: if agent wrote spin-down, patch duration_s; if not, write idle fallback.
    if [[ -s "$PROJECT/beat-log.jsonl" ]]; then
        last=$(tail -1 "$PROJECT/beat-log.jsonl")
        last_outcome=$(printf '%s' "$last" | jq -r '.outcome // ""')
        if [[ "$last_outcome" == "in_progress" ]]; then
            printf '%s\n' "$(jq -cn \
                --arg t "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
                --argjson d "$BEAT_ELAPSED" \
                '{"last_run_at":$t,"ticket_id":null,"branch":null,"PR":null,
                  "outcome":"idle","diagnostics":"no ticket picked","duration_s":$d}')" \
                >> "$PROJECT/beat-log.jsonl"
        else
            patched=$(printf '%s' "$last" | jq --argjson d "$BEAT_ELAPSED" '. + {duration_s: $d}')
            tmp=$(mktemp)
            head -n -1 "$PROJECT/beat-log.jsonl" > "$tmp"
            printf '%s\n' "$patched" >> "$tmp"
            mv "$tmp" "$PROJECT/beat-log.jsonl"
        fi
    fi
fi

jq -cs 'last' "$PROJECT/beat-log.jsonl" 2>/dev/null || true
echo "=== $SKILL done $(date -u +%FT%TZ) ==="
