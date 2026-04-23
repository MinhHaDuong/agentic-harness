#!/usr/bin/env bash
# Detect consumer-project assumptions leaking into harness skills and tickets.
# Usage: check-project-leak.sh [dir ...]   (default: skills tickets)
# Escape hatch: add  <!-- harness-extension-point -->  on the same or preceding line.
set -euo pipefail

if [ $# -eq 0 ]; then
    DIRS=(skills tickets)
else
    DIRS=("$@")
fi

# Patterns checked everywhere (skills + tickets)
GLOBAL_PATTERNS=(
    '/home/haduong/CNRS/papiers'
)

# Patterns checked only in skills/ (not ticket bodies, where examples are expected)
SKILL_PATTERNS=(
    'uv run pytest'
)

fail=0

check_pattern() {
    local pattern="$1" dir="$2"
    [ -d "$dir" ] || { echo "WARN: directory not found: $dir" >&2; return; }
    while IFS= read -r match; do
        [ -z "$match" ] && continue
        file="${match%%:*}"
        rest="${match#*:}"
        lineno="${rest%%:*}"
        line="${rest#*:}"
        prev=""
        if [ "$lineno" -gt 1 ]; then
            prev=$(sed -n "$((lineno - 1))p" "$file")
        fi
        if echo "$line $prev" | grep -q 'harness-extension-point'; then
            continue
        fi
        echo "LEAK [$pattern]: $file:$lineno: $line"
        fail=1
    done < <(grep -rn "$pattern" "$dir" 2>/dev/null || true)
}

for dir in "${DIRS[@]}"; do
    for pattern in "${GLOBAL_PATTERNS[@]}"; do
        check_pattern "$pattern" "$dir"
    done
done

for dir in "${DIRS[@]}"; do
    # Skill patterns only apply to skills directories
    case "$dir" in
        skills*|*/skills*)
            for pattern in "${SKILL_PATTERNS[@]}"; do
                check_pattern "$pattern" "$dir"
            done
            ;;
    esac
done

exit $fail
