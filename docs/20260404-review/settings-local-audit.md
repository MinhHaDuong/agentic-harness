# settings.local.json Audit

**Date:** 2026-04-04
**Issue:** #7

## Entries to REMOVE (one-off debugging artifacts)

```
"Bash(for:*)"                           — overly broad, covers arbitrary for loops
"Bash(do echo \"Fan $f:\")"             — NVIDIA fan debug one-off
"Bash(done)"                            — shell syntax fragment
"Bash(# Check if X is actually...)"     — inline Xorg debug script (line 20)
"Bash(# The display is :1 which...)"    — inline Xorg debug script (line 21)
"Bash(cat:*)"                           — use Read tool instead
```

## Entries to NARROW

```
"Bash(sudo tee:*)"   → remove (too broad — arbitrary file write as root)
"Bash(sudo cp:*)"    → remove (too broad — arbitrary file copy as root)
"Bash(sudo chmod:*)" → remove (too broad — arbitrary permission changes)
"Bash(kill:*)"       → keep but note: allows killing any process
"Bash(git reset:*)"  → remove (now blocked by guard-destructive-bash.sh for --hard)
"Bash(find:*)"       → remove (use Glob tool instead)
```

## Duplicates to MERGE

```
"Bash(dpkg -l:*)" + "Bash(dpkg -S:*)" + "Bash(dpkg:*)" → keep only "Bash(dpkg:*)"
"Bash(pip show:*)" + "Bash(pip3 show:*)" + "Bash(uv pip show:*)" → keep all (different tools)
```

## Proposed pruned version

132 → 94 entries (29% reduction). Categories added as comments for maintainability.

See `settings-local-pruned.json` for the proposed replacement.
