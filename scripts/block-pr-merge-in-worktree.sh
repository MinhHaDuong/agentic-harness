#!/bin/bash
set -euo pipefail
# Block "gh pr merge" inside a git worktree.
# Matcher in settings.json ensures this only runs for "gh pr merge" commands.

cat > /dev/null  # consume stdin

if [ -f .git ] && grep -q "gitdir:" .git 2>/dev/null; then
  cat >&2 <<'EOF'
Blocked: gh pr merge fails in git worktrees (main is locked by parent).
Use the GitHub API directly:

  PR=NUMBER
  gh api "repos/{owner}/{repo}/pulls/$PR/merge" -X PUT -f merge_method=squash
  gh api "repos/{owner}/{repo}/pulls/$PR" --jq .head.ref | xargs -I{} git push origin --delete {}
EOF
  exit 2
fi

exit 0
