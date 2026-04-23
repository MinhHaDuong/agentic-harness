#!/usr/bin/env bash
# Detect consumer-project assumptions leaking into harness skills and tickets.
# Patterns that flag: hard-coded absolute paths to consumer projects.
# Escape hatch: add  <!-- harness-extension-point -->  on the same or preceding line.
set -euo pipefail

TARGETS=(skills tickets)
PATTERN='/home/haduong/CNRS/papiers'

fail=0

for dir in "${TARGETS[@]}"; do
    while IFS= read -r match; do
        file="${match%%:*}"
        lineno="${match#*:}"; lineno="${lineno%%:*}"
        line="${match#*:*:}"

        # Escape hatch: same line or look at previous line in file
        prev=""
        if [ "$lineno" -gt 1 ]; then
            prev=$(sed -n "$((lineno - 1))p" "$file")
        fi

        if echo "$line $prev" | grep -q 'harness-extension-point'; then
            continue
        fi

        echo "LEAK: $file:$lineno: $line"
        fail=1
    done < <(grep -rn "$PATTERN" "$dir" 2>/dev/null || true)
done

exit $fail
