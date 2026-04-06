#!/bin/bash
# Warn if any rules/*.md file hasn't been reviewed in 30+ days.
# Advisory only — always exits 0.

STALE_DAYS=30
now=$(date +%s)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"

for f in "$PLUGIN_ROOT"/skills/harness-rules/*.md; do
    date_str=$(grep -oP 'last-reviewed:\s*\K\d{4}-\d{2}-\d{2}' "$f" 2>/dev/null)
    [ -z "$date_str" ] && continue
    reviewed=$(date -d "$date_str" +%s 2>/dev/null) || continue
    age_days=$(( (now - reviewed) / 86400 ))
    if [ "$age_days" -ge "$STALE_DAYS" ]; then
        echo "⚠ STALE RULE: $f last reviewed $date_str ($age_days days ago)"
    fi
done

exit 0
