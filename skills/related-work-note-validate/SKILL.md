---
name: related-work-note-validate
description: Re-resolve every DOI/URL/eprint in a related-work-note's Bibliography. Append a provenance line to Methods. One-line verdict to stdout (PASS / WARN / FAIL).
disable-model-invocation: false
user-invocable: true
argument-hint: <note-file-path>
---

# Related-work-note validator

Re-resolve every identifier in the note's Bibliography via WebFetch.
Flag entries with no DOI, URL, or eprint as unverifiable. Append a
single provenance bullet to the `## Methods` section. Print a
one-line verdict to stdout.

## Constraints (non-obvious)

- **Append-only.** Use `Edit` to add one bullet to Methods. Never
  rewrite the note with `Write`. Never touch cited-work bodies or
  the Bibliography section.
- **Three verdicts.** PASS (all resolved), WARN (some entries have
  no identifier), FAIL (at least one fetch failed).
- **Network errors are not citation failures.** Three consecutive
  network errors → escalate, not FAIL.
- **One-line stdout.** Downstream tooling greps it:
  `PASS`, `WARN: {U} of {N} entries have no DOI/URL`, or
  `FAIL: {K} entries unresolved, {U} unverifiable` — followed by
  the note path. Nothing else on stdout.
- **Abort, don't guess.** If the file lacks `## Bibliography` or
  `## Methods`, stop with an error.

## Identifier fields to check

`doi`, `url`, `eprint` (HAL/arXiv). Prefer DOI when multiple are
present. Entries with none of these three → unverifiable.

## Methods bullet format

```
- **Validator (external check).** {VERDICT} — {summary}.
  Checked {YYYY-MM-DDThh:mmZ} by related-work-note-validate.
```
