---
name: verify-adherence
description: Check a branch's diff against project rules. Mechanical-first — runs hygiene tests + grep ratchet before falling back to LLM. Emits suggested tests for any semantic finding so the LLM surface shrinks over time.
disable-model-invocation: false
user-invocable: true
argument-hint: <branch-or-pr-number>
context: fork
---

# Verify adherence — $ARGUMENTS

Enforce the project's `.claude/rules/*.md` conventions on a branch or PR. **Prefer tests
over LLM checks.** If a rule can be mechanized, the skill's job is to run the test or grep.
An LLM subagent is the fallback for semantic residue only.

## Philosophy: ratchet toward mechanical

Every time the semantic fallback flags a violation, the skill emits a `suggested_test`
entry proposing how to mechanize that rule. Over time the LLM surface shrinks. New test →
rule is permanently enforced → never needs LLM again.

## When to use

- Called by `/verify` as part of phase 2.
- Called standalone by an author who wants to pre-check their own branch before opening a PR.
- Called by the orchestrator in an Imagine phase to audit a prototype.

## Input

One argument: a branch name or PR number. Resolve PR → branch via `gh pr view --json headRefName`.

## Phases

### 1.0 Cheap static checks (always first, budget <10 s)

Runs before anything else in the mechanical phase. Two sub-checks, both **blocking**;
failure stops the phase here and does not fall through to 1/2/3. Combined budget <10 s.

**(a) Import resolution.** Parse the diff for every symbol referenced in touched modules
under `scripts/`. For each `(module, name)` pair:

```bash
uv run python -c "import sys; sys.path.insert(0, 'scripts'); import <module>; getattr(<module>, '<symbol>')"
```

Scope: touched `.py` files under `scripts/`. Modules outside that tree are not probed.

Catches the formatter-strip-import class of bug: tests are green, but the first real run
`NameError`s because an auto-formatter dropped the import line for a just-used symbol.
Any unresolved symbol → fail with rule ref `verify-adherence#import-resolution`, record
`{module, name, file:line}`.

**(b) Per-module test run.** For each touched module, run its matching test file(s):

```bash
uv run python -m pytest <touched-modules-test-files> -q
```

Catches per-module regressions seconds after the edit, before the full hygiene suite or
deep review pays the cost. Failures record as `{test_id, rule_ref, file:line}` with rule
ref `verify-adherence#per-module-tests`.

Both checks are intentionally cheap. If either exceeds the 10 s budget, trim scope (fewer
symbols, fewer test files) rather than skipping.

### 1. Mechanical suite (always first, never skip)

Run the hygiene + discipline tests. These are cheap and definitive:

```bash
uv run python -m pytest \
    tests/test_script_hygiene.py \
    tests/test_io_discipline.py \
    tests/test_schema_contracts.py \
    -q
```

Plus any other test files whose names start with `test_hygiene_` or `test_discipline_`.

Failures here are **blocking**. Record each as `{test_id, rule_ref, file:line}`.

### 2. Grep ratchet (the cheap, fast rules)

Run a bank of `rg` patterns. Each pattern corresponds to a single rule and carries the
rule reference explicitly. Run against the diff (not the whole repo) via
`git diff main...HEAD --name-only | xargs rg -n PATTERN`.

Minimum starting bank (extend as rules get mechanized):

| Rule | Pattern | Rule ref |
|------|---------|----------|
| `fig.savefig(` forbidden (use `save_figure`) | `rg 'fig\.savefig\('` | `architecture.md` rule 5 |
| Direct corpus reads forbidden | `rg 'pd\.read_(csv\|feather).*refined_(works\|embeddings\|citations)'` | `architecture.md` rule 9 |
| Hardcoded random seed | `rg '(seed\s*=\s*42\|RandomState\(42\))'` | `architecture.md` rule 7 |
| `print(` in non-script modules | `rg 'print\(' scripts/_` | `coding.md` logging rule |
| Bare `logging.getLogger` | `rg 'logging\.getLogger'` | `coding.md` logging rule |
| Hardcoded `"data/catalogs"` paths | `rg '"data/catalogs/'` | `architecture.md` data location |

Failures here are **blocking**. Record as `{pattern, rule_ref, file:line}`.

### 3. Semantic subagent (fallback only)

Only runs if any `.claude/rules/*.md` file changed OR if the diff touches architectural
concerns not covered by phases 1–2. Spin **one** subagent with:

- The diff.
- The relevant `.claude/rules/*.md` files.
- Prompt: "For each rule section, cite one piece of evidence that the diff either adheres
  to or violates it. Only flag concrete violations with file:line anchors. For every
  violation, suggest a grep pattern or test that could catch it mechanically next time."

Output: `{rule_section, concern, file:line, severity, suggested_test}`.

**Hard constraints** on the subagent:
- Must cite file:line for every finding.
- Must propose a `suggested_test` for every semantic finding — no exceptions.
- Must not flag hypotheticals ("could be a problem if…"). Only concrete violations.

### 4. Emit verdict

```yaml
adherence: PASS | FAIL
mechanical_failures:
  - test_or_grep: <id>
    rule_ref: <.claude/rules/foo.md#section>
    file: <path>
    line: <n>
semantic_findings:
  - rule_section: <.claude/rules/architecture.md#phase-2-rule-4>
    concern: <one sentence>
    file: <path>
    line: <n>
    severity: blocking | nit
    suggested_test: <grep pattern or pytest snippet>
untested_rules:
  - rule: <.claude/rules/foo.md#bar>
    suggested_test: <code>
```

## Ratchet discipline

After each run, if `semantic_findings` is non-empty:

1. The caller (`/verify` or author) opens a small follow-up ticket: "Mechanize adherence
   rule X per suggested_test."
2. That ticket converts the LLM check into a test in `tests/test_hygiene_<rule>.py`.
3. Next invocation of `/verify-adherence`, the rule is caught by phase 1 instead of
   phase 3. LLM surface shrinks permanently.

This ratchet is the whole point. Do not accept `semantic_findings` as a steady state.

## Circuit breakers

- Phase 1.0 cannot run (e.g., `uv` missing, `scripts/` unreadable) → ESCALATE; don't
  silently skip. A broken cheap-check layer defeats the point.
- Phase 1 fails to run (env broken) → ESCALATE; don't fall through.
- Semantic subagent output lacks `file:line` or `suggested_test` → reject the output and
  flag as adherence-infrastructure bug. Don't silently accept.
- Grep bank explodes in size (>30 patterns) → migrate patterns to proper pytest files and
  trim.

## Not in scope

- Writing style / AI-tells (handled by `/review-pr-prose` and `config/ai-tells.yml`).
- Ticket format (enforced by pre-commit hook).
- Git branch naming (enforced by pre-commit hook).
- Merging decisions. This skill never affects merge state.
