# Review 4: Imperial Dragon Harness — Multi-Perspective PR Review

**Date:** 2026-04-04
**Reviewer:** Opus agent (5-perspective code review)

---

## 1. Correctness Reviewer

| # | Finding | Severity |
|---|---------|----------|
| 1 | `.env` contains plaintext `ZOTERO_API_KEY` loaded into every session via `persist_env` | Critical |
| 2 | `block-pr-merge-in-worktree.sh` matcher `Bash(gh pr merge*)` doesn't account for env-prefixed commands | Minor |
| 3 | `on-start.sh:12` — `exit 0` on missing `CLAUDE_PROJECT_DIR` skips user-level `.env` loading | Major |
| 4 | `on-start.sh:9` — `git pull --ff-only` failure silently swallowed (`2>/dev/null`) | Minor |
| 5 | `sed 's/^export //'` fragile for edge cases in `.env` parsing | Nit |
| 6 | No JSON schema validation for settings files | Minor |
| 7 | STATE.md `## Next actions` has only 2 items vs. prescribed 5-10 | Nit |

**Verdict: Request Changes** (finding #3 is a functional bug — user-level env skipped when no project dir)

---

## 2. Security Reviewer

| # | Finding | Severity |
|---|---------|----------|
| 1 | Plaintext API key in `.env` propagated to `CLAUDE_ENV_FILE` | Critical |
| 2 | `skipDangerousModePermissionPrompt: true` with only one PreToolUse guard | Critical |
| 3 | `settings.local.json` allows `sudo tee:*`, `sudo cp:*`, `sudo chmod:*`, `git reset:*`, `kill:*` | Major |
| 4 | Auto-pull from remote is a supply-chain vector (no signature verification) | Major |
| 5 | `core.hooksPath hooks` could activate malicious project hooks | Minor |
| 6 | `.env` loaded before project validation | Nit |

**Verdict: Request Changes** (`skipDangerousModePermissionPrompt` + broad `sudo` allowances = significant attack surface)

---

## 3. Consistency Reviewer

| # | Finding | Severity |
|---|---------|----------|
| 1 | `workflow.md` references `EnterWorktree`/`ExitWorktree` but no hook enforces them | Major |
| 2 | `git.md:3` says "Main is read-only" but nothing enforces it | Major |
| 3 | Hook naming inconsistent: `on-start` (event name) vs `block-pr-merge-in-worktree` (function description) | Minor |
| 4 | Only `rules/state.md` has YAML frontmatter; other rules files don't | Minor |
| 5 | `.gitignore` whitelists `settings.template.json` but file doesn't exist | Nit |
| 6 | `docs/` contains climate finance reviews unrelated to harness | Minor |

**Verdict: Request Changes** (stated rules vs. enforced rules gap erodes trust)

---

## 4. Scope / Complexity Reviewer

| # | Finding | Severity |
|---|---------|----------|
| 1 | `settings.local.json` is 140-line append-only audit log, not curated policy | Major |
| 2 | `docs/` mixes harness design docs with unrelated research outputs | Major |
| 3 | `commands/gsd/` — 25+ third-party files; unclear if actively used | Minor |
| 4 | STATE.md mixes engineering tasks with intellectual review tasks | Minor |
| 5 | Missing from harness vs. STATE.md goals: staleness detection, offline tickets, telemetry, multi-machine sync | Minor |
| 6 | Skills not referenced in any harness documentation | Nit |

**Verdict: Approve with reservations** (core well-scoped; accumulated cruft needs cleanup)

---

## 5. Documentation Reviewer

| # | Finding | Severity |
|---|---------|----------|
| 1 | No single doc explains harness architecture (what files exist, how they interact) | Major |
| 2 | `on-start.sh` STATE.md output only works when `CLAUDE_PROJECT_DIR` is set | Major |
| 3 | `workflow.md` decision table is excellent — clear, unambiguous | (Strength) |
| 4 | `coding.md` at 43 lines — well under recommended threshold | (Strength) |
| 5 | `braindump-harness-extraction.md` references old "Oeconomia" naming, unclear if current | Minor |
| 6 | Settings split rationale documented only in `.gitignore` comments | Minor |
| 7 | Forsythe principles doc not integrated into rules — connection is implicit | Nit |

**Verdict: Approve with reservations** (rules are good; docs layer needs organization)

---

## Overall Verdict: Request Changes

### Top 5 Actionable Items

1. **Fix `on-start.sh` early exit bug** — split hook so user-level `.env` loading happens unconditionally, project-level operations gated on directory check
2. **Audit and prune `settings.local.json`** — remove one-off inline commands, review `sudo` grants, document intended policy
3. **Re-evaluate `skipDangerousModePermissionPrompt: true`** — add compensating PreToolUse hooks for destructive operations, or remove the flag
4. **Clean up `docs/`** — move unrelated research outputs; add index explaining each document
5. **Add enforcement for "main is read-only"** — pre-commit hook blocking direct commits to main, or soften the rule to match reality
