---
name: related-work-note-validate
description: Re-resolve every DOI/URL/eprint in a related-work-note's Bibliography. Append a provenance line to Methods. One-line verdict to stdout (PASS / WARN / FAIL).
disable-model-invocation: false
user-invocable: true
argument-hint: <note-file-path>
---

# Related-work-note validator

Re-resolve every identifier in the note's Bibliography. Flag entries
with no DOI, URL, or eprint as unverifiable. Append a single provenance
bullet to the `## Methods` section. Print a one-line verdict to stdout.

## Constraints (non-obvious)

- **Append-only.** Use `Edit` to add one bullet to Methods. Never
  rewrite the note with `Write`. Never touch cited-work bodies or
  the Bibliography section.
- **Three verdicts.** PASS (all resolved), WARN (some entries have
  no identifier), FAIL (at least one fetch failed).
- **Network errors are not citation failures.** Three consecutive
  connection errors → script exits with code 2 (escalate, not FAIL).
- **One-line stdout.** Downstream tooling greps it:
  `PASS`, `WARN: {U} of {N} entries have no DOI/URL`, or
  `FAIL: {K} fetch failures` — followed by the note path.
  Nothing else on stdout.
- **Abort, don't guess.** If the file lacks `## Bibliography` or
  `## Methods`, stop with an error.

## Identifier fields to check

`doi`, `url`, `eprint`+`eprinttype` (arXiv/HAL). Prefer DOI when
multiple are present. Entries with none of these → unverifiable.

## Step 1 — run the validator script (exactly one Bash call)

```
python3 ~/.claude/scripts/validate-refs.py <note-file>
```

The script:
- Parses `## Bibliography`, extracts `doi`/`url`/`eprint`+`eprinttype`
- Resolves each: DOI via `https://doi.org/`, arXiv via `https://arxiv.org/abs/`,
  HAL via `https://hal.science/`, plain URL directly
- Per-entry detail lines go to **stderr** (`[OK|WARN|FAIL] key: url (status)`)
- Final verdict goes to **stdout** (single greppable line)
- Exit 0 = PASS or WARN, exit 1 = FAIL, exit 2 = network escalation, exit 3 = parse error

Capture both stdout (verdict) and stderr (per-entry detail) separately.

## Step 2 — append provenance bullet to Methods (LLM, always)

Use `Edit` to append one bullet to `## Methods`:

```
- **Validator (external check).** {VERDICT} — {summary}.
  Checked {YYYY-MM-DDThh:mmZ} by related-work-note-validate.
```

Fill `{VERDICT}` from the script's stdout. Fill `{summary}` with
counts from stderr (e.g., "3 OK, 1 unverifiable, 0 failed").

## Step 3 — annotate failures (LLM, only on FAIL or escalation)

If the script exits 1 (FAIL): for each `[FAIL]` line from stderr,
suggest a corrected identifier or note why the URL may be broken.

If the script exits 2 (network escalation): report the network
issue and ask the user to retry later. Do not mark entries as failed.

## Methods bullet format

```
- **Validator (external check).** {VERDICT} — {summary}.
  Checked {YYYY-MM-DDThh:mmZ} by related-work-note-validate.
```
