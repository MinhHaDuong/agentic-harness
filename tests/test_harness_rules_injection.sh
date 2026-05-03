#!/usr/bin/env bash
# Regression test for ticket 0042 — harness-rules index-based lazy load.
#
# Asserts that scripts/on-start.sh emits the harness-rules index
# (skills/harness-rules/README.md) before its stdout cutoff, but does
# NOT emit the bodies of individual rule files. Agents read those on
# demand via the index pointers.
set -euo pipefail

cd "$(dirname "$0")/.."
fail=0

out=$(bash scripts/on-start.sh 2>&1 || true)

# 1. Index headers/scope signals must appear in the hook output.
for needle in "workflow.md" "git.md" "always" "condition"; do
  if ! grep -qF "$needle" <<<"$out"; then
    echo "FAIL: hook output missing index marker '$needle'"
    fail=1
  fi
done

# 2. Rule-body sentences must NOT appear — the index injects pointers,
#    not contents. Pick one distinctive sentence per file.
declare -a body_strings=(
  # workflow.md
  "Reviewers use a different model than the coder."
  # git.md
  "Main is read-only except for STATE housekeeping."
  # coding-python.md
  "always \`uv sync\`"
)
for needle in "${body_strings[@]}"; do
  if grep -qF "$needle" <<<"$out"; then
    echo "FAIL: hook output leaked rule body content: '$needle'"
    fail=1
  fi
done

# 3. on-start.sh must literally contain a `cat ... README.md` invocation.
if ! grep -F 'cat' scripts/on-start.sh | grep -qF 'README.md'; then
  echo "FAIL: scripts/on-start.sh missing 'cat ... README.md' invocation"
  fail=1
fi

# 4. SKILL.md must be gone (the persuasion-phrase wrapper is replaced).
if [[ -e skills/harness-rules/SKILL.md ]]; then
  echo "FAIL: skills/harness-rules/SKILL.md still exists"
  fail=1
fi

# 5. README.md index must exist.
if [[ ! -f skills/harness-rules/README.md ]]; then
  echo "FAIL: skills/harness-rules/README.md missing"
  fail=1
fi

if (( fail )); then
  exit 1
fi
echo "PASS: harness-rules index injection wired correctly"
