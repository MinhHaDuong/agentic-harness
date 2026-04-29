#!/usr/bin/env bash
# Structural regression test for ticket 0045 — orchestrator → raid rename.
# Asserts that no live skill, script, or doc still uses the /orchestrator
# slash command, while ticket history remains untouched and the nightbeat
# log parser dual-accepts both labels.
set -euo pipefail

cd "$(dirname "$0")/.."
fail=0

# 1. No /orchestrator slash invocations in live surfaces
#    (scripts/nightbeat-report.py is allowed to keep the bare
#    "orchestrator:" log-label prefix for dual-accept parsing.)
hits=$(grep -rn '/orchestrator' skills/ scripts/ commands/ README.md STATE.md bin/ 2>/dev/null || true)
if [[ -n "$hits" ]]; then
  echo "FAIL: /orchestrator still referenced in live code:"
  echo "$hits"
  fail=1
fi

# 2. Ticket history preserved (/orchestrator remains in old tickets)
ticket_hits=$(grep -rln '/orchestrator' tickets/ 2>/dev/null | wc -l)
if (( ticket_hits < 1 )); then
  echo "FAIL: expected /orchestrator references in tickets/ (history); found $ticket_hits"
  fail=1
fi

# 3. nightbeat-report parser dual-accepts both prefixes.
#    Source-level check: the parser must mention both labels.
if ! grep -q '"orchestrator:"' scripts/nightbeat-report.py; then
  echo "FAIL: nightbeat-report.py no longer accepts the legacy 'orchestrator:' label"
  fail=1
fi
if ! grep -q '"raid:"' scripts/nightbeat-report.py; then
  echo "FAIL: nightbeat-report.py does not accept the new 'raid:' label"
  fail=1
fi

# 4. Skill directory renamed
if [[ -e skills/orchestrator ]]; then
  echo "FAIL: skills/orchestrator still exists"
  fail=1
fi
if [[ ! -f skills/raid/SKILL.md ]]; then
  echo "FAIL: skills/raid/SKILL.md missing"
  fail=1
fi
if ! grep -q '^name: raid$' skills/raid/SKILL.md; then
  echo "FAIL: skills/raid/SKILL.md frontmatter name is not 'raid'"
  fail=1
fi

if (( fail )); then
  exit 1
fi
echo "PASS: orchestrator → raid rename is structurally consistent"
