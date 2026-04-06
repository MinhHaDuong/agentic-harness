#!/bin/bash
# Stop hook (prompt type): remind to run tests if code was changed.
# Outputs a message that Claude sees before finishing — advisory, not blocking.

# Check if any Python files were modified in this session (uncommitted or recent commits)
py_changed=false

# Check working tree
if git diff --name-only HEAD 2>/dev/null | grep -q '\.py$'; then
    py_changed=true
fi

# Check staged
if git diff --cached --name-only 2>/dev/null | grep -q '\.py$'; then
    py_changed=true
fi

if [ "$py_changed" = true ]; then
    # Check if pytest was run (look for .pytest_cache or recent test output)
    if [ ! -d .pytest_cache ] || [ "$(find .pytest_cache -maxdepth 1 -newer "$(git rev-parse --git-dir)/index" 2>/dev/null | head -1)" = "" ]; then
        echo "WARNING: Python files were modified but tests may not have been run. Consider: make check-fast"
    fi
fi

exit 0
