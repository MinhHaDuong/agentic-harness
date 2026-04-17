#!/usr/bin/env bash
# Deep docs-freshness verification: detect closed git-erg tickets still listed
# as TODO in canonical status/directive docs at the repo root. Gracefully
# degrades when git-erg tickets are absent (exits 0 with a skip message).
#
# Exits 0 if clean or if ticket cross-check is skipped. Exits 1 only on stale
# references. Designed to be called from the healthcheck skill.

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "not a git repository; cannot run docs-freshness" >&2
  exit 0
}
cd "$repo_root"

if ! compgen -G "tickets/*.erg" > /dev/null; then
  echo "skip: no tickets/*.erg files found (git-erg not in use)"
  exit 0
fi

closed_ids=$(grep -l '^Status: closed' tickets/*.erg 2>/dev/null \
  | sed -E 's|.*/([0-9]{4})-.*|\1|' \
  | sort -u)

docs=(STATE.md MASTERPLAN.md README.md ROADMAP.md ARCHITECTURE.md)
stale_count=0
scanned_count=0

for doc in "${docs[@]}"; do
  [[ -f "$doc" ]] || continue
  scanned_count=$((scanned_count + 1))

  last_commit=$(git log -1 --format=%ci -- "$doc" 2>/dev/null || echo "never committed")
  echo "=== $doc (last commit: $last_commit) ==="

  todo_lines=$(awk '
    /^## /{section=$0}
    /\[ \]/ {print NR":"$0; next}
    section ~ /Next actions|Open tickets/ && /[0-9]{4}/ {print NR":"$0}
  ' "$doc")

  if [[ -z "$todo_lines" ]]; then
    echo "  (no TODO-context lines with ticket references)"
    continue
  fi

  while IFS=: read -r lineno content; do
    for tid in $closed_ids; do
      if [[ "$content" == *"$tid"* ]]; then
        echo "  STALE: $doc:$lineno — ticket $tid listed as TODO but Status: closed"
        stale_count=$((stale_count + 1))
      fi
    done
  done <<< "$todo_lines"
done

echo ""
echo "SUMMARY: $scanned_count docs scanned, $stale_count stale ticket references"

if [[ $stale_count -gt 0 ]]; then
  exit 1
fi
exit 0
