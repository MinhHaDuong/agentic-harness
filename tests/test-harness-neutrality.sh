#!/usr/bin/env bash
# Self-test for scripts/check-harness-neutrality.sh
#
# Creates a temporary git repo, stages leaky and clean files, and verifies
# that the checker exits 1 on leakage and 0 when escape hatches suppress matches.
#
# Run from any directory: bash tests/test-harness-neutrality.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHECKER="$REPO_ROOT/scripts/check-harness-neutrality.sh"

pass=0
fail=0

ok() {
    echo "PASS: $1"
    pass=$((pass + 1))
}

fail_test() {
    echo "FAIL: $1"
    fail=$((fail + 1))
}

# Create a temp git repo for isolated testing
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

git -C "$TMPDIR" init -q
git -C "$TMPDIR" config user.email "test@example.com"
git -C "$TMPDIR" config user.name "Test"

# Make an empty initial commit so HEAD exists
git -C "$TMPDIR" commit -q --allow-empty -m "init"

mkdir -p "$TMPDIR/skills/testskill" "$TMPDIR/tickets"

# --- Test 1: leaked pattern in skills/ → checker must exit 1 ---
cat > "$TMPDIR/skills/testskill/SKILL.md" <<'EOF'
# Test skill
Climate_finance pipeline integration.
EOF
git -C "$TMPDIR" add "skills/testskill/SKILL.md"

# Run the checker in the temp repo (BASE=HEAD → git diff --cached)
actual_exit=0
(
    cd "$TMPDIR"
    bash "$CHECKER" HEAD 2>&1
) && actual_exit=0 || actual_exit=$?

if [ "$actual_exit" -eq 1 ]; then
    ok "leak in skills/SKILL.md caught (exit 1)"
else
    fail_test "leak in skills/SKILL.md not caught (expected exit 1, got $actual_exit)"
fi

# --- Test 2: escape hatch suppresses match → checker must exit 0 ---
cat > "$TMPDIR/skills/testskill/SKILL.md" <<'EOF'
# Test skill

<!-- harness-extension-point -->
Climate_finance pipeline integration.
EOF
git -C "$TMPDIR" add "skills/testskill/SKILL.md"

(
    cd "$TMPDIR"
    bash "$CHECKER" HEAD 2>&1
) && actual_exit=0 || actual_exit=$?

if [ "$actual_exit" -eq 0 ]; then
    ok "escape hatch suppresses match (exit 0)"
else
    fail_test "escape hatch not working (expected exit 0, got $actual_exit)"
fi

# --- Test 3: AEDIST pattern caught in tickets/ ---
cat > "$TMPDIR/tickets/9999-test.erg" <<'EOF'
%erg v1
Title: test
Status: open
Created: 2026-04-23
Author: test

--- log ---
2026-04-23T00:00Z test created

--- body ---
AEDIST uses this approach.
EOF
# Clear skills leak first
cat > "$TMPDIR/skills/testskill/SKILL.md" <<'EOF'
# Test skill
No project references here.
EOF
git -C "$TMPDIR" add "tickets/9999-test.erg" "skills/testskill/SKILL.md"

(
    cd "$TMPDIR"
    bash "$CHECKER" HEAD 2>&1
) && actual_exit=0 || actual_exit=$?

if [ "$actual_exit" -eq 1 ]; then
    ok "AEDIST leak in tickets/ caught (exit 1)"
else
    fail_test "AEDIST leak in tickets/ not caught (expected exit 1, got $actual_exit)"
fi

# --- Test 4: clean staged changes → checker must exit 0 ---
cat > "$TMPDIR/tickets/9999-test.erg" <<'EOF'
%erg v1
Title: test
Status: open
Created: 2026-04-23
Author: test

--- log ---
2026-04-23T00:00Z test created

--- body ---
Generic workflow documentation only.
EOF
git -C "$TMPDIR" add "tickets/9999-test.erg"

(
    cd "$TMPDIR"
    bash "$CHECKER" HEAD 2>&1
) && actual_exit=0 || actual_exit=$?

if [ "$actual_exit" -eq 0 ]; then
    ok "clean staged changes pass (exit 0)"
else
    fail_test "clean staged changes wrongly flagged (expected exit 0, got $actual_exit)"
fi

# --- Summary ---
echo ""
echo "Results: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
