---
name: bib-merge
description: Merge the Bibliography block of a `related-work-note` output into a project's `refs.bib`. Parses the note's ```bibtex fence, dedupes against the existing library on first-author surname + year, flags DOI/URL conflicts, preserves the library's key style, and appends new entries. Reports merged / skipped / deduped / conflicts. Optional `--dry-run` reports without writing.
disable-model-invocation: false
user-invocable: true
argument-hint: <note-file-path> [<refs-bib-path>] [--dry-run]
---

# Bibliography merge

**Purpose.** The `related-work-note` skill emits a Bibliography
section of BibTeX entries inside a markdown note, and deliberately
does **not** touch the manuscript's `refs.bib` — the author reviews
citations before they enter the canonical bibliography. After
approval, those entries still have to land in `refs.bib`. Doing it
by hand drops fields, duplicates entries under different keys, and
pollutes the key space. This skill closes the loop: parse note,
dedupe, merge, report.

**Scope.** One invocation = one note file merged into one
`refs.bib`. The skill touches exactly two things: it reads the
note, and it may append to (never rewrite) `refs.bib`. Crossref
enrichment, removal of unreferenced entries, and reordering
`refs.bib` are explicitly out of scope (see ticket 0012).

**Relationship.** Consumes output of `related-work-note`.
Orthogonal to `related-work-note-validate` (ticket 0011): this
skill trusts the note's Bibliography is well-formed; validation is
a separate pass the caller can run first.

## When to use

- After the author has reviewed and approved a `related-work-note`
  output and wants its citations promoted into the project's
  `refs.bib`.
- When collating several approved notes into one canonical
  bibliography (one invocation per note).
- As a post-approval step in the Related Work workflow (e.g.,
  AEDIST journal paper §2).

Do **not** invoke this skill on an unreviewed note, on a note that
has not passed `related-work-note-validate`, or speculatively as
part of note generation. The point of the two-step design is that
the author approves first.

## Input

Positional arguments:

1. **Note file path** (required). Repository-relative path to a
   markdown file previously emitted by `related-work-note`. Must
   contain a `## Bibliography` section followed by a fenced
   ```bibtex block.
2. **refs.bib path** (optional). Target BibTeX file. Default:
   `report/refs.bib` relative to cwd if that file exists. If no
   path is provided and the default does not exist, abort with a
   one-line error — do not guess.
3. **`--dry-run`** flag (optional). When set, run the entire merge
   logic but do not modify `refs.bib`. Print the same report as a
   normal run, prefixed with `DRY-RUN:`. The note file is never
   modified regardless.

If the note file is missing, unreadable, or lacks a
```bibtex-fenced Bibliography block, abort with a one-line error.

## Steps

### 1. Read inputs

- `Read` the note file. Locate the `## Bibliography` heading and
  the first ```bibtex fenced block below it. Extract the fence
  content verbatim. If either the heading or the fence is missing,
  print `ERROR: note has no bibtex fence in Bibliography` and stop.
- `Read` the `refs.bib` path. If the file exists, load all of it.
  If the file does not exist at the caller-supplied path, abort;
  if it does not exist at the default path and the caller did not
  supply one, abort. This skill **does not create** `refs.bib` —
  that is a project-setup decision, not a merge decision.

### 2. Parse entries

Parse both the note's bibtex fence and the existing `refs.bib`
into entry records. For each entry capture:

- entry type (`@article`, `@inproceedings`, `@misc`, …),
- entry key (the token between `{` and the first `,`),
- field map (normalized field name → value; strip outer braces and
  surrounding whitespace),
- the **raw text** of the entry as it appears in the source,
  including its exact indentation and trailing newline.

Preserve the raw text for every existing `refs.bib` entry so the
file can be appended to without rewriting or reformatting any
existing block.

### 3. Detect the library's key and format style

Inspect the existing `refs.bib` entries to infer project
conventions:

- **Key style.** Classify each existing key as one of:
  - `zotero8` — exactly 8 uppercase-alphanumeric characters
    (e.g., `LYGDCQCL`),
  - `author-year` — `Surname` + 4-digit year, optional suffix
    (e.g., `Gotzens2019`, `Smith2021a`),
  - `other` — anything else.
  Take the majority class as the project's style. If the file has
  fewer than three entries or no majority, treat the style as
  `unknown` and keep the note's key verbatim (a matching style is
  best-effort; blocking the merge on ambiguity would be worse than
  a cosmetic mismatch — record this in the report).
- **Field order.** The order in which fields typically appear in
  existing entries (e.g., `author, title, year, journal, doi,
  url`). Take the most common prefix-order across the file.
- **Indentation.** The leading whitespace before field lines (two
  spaces, four spaces, or tab). Take the majority.
- **Key–equals spacing.** Whether entries use `author = {…}` or
  `author={…}` or `author  = {…}`. Take the majority.

These are formatting hints for **new** entries only. Never
reformat an existing entry.

### 4. For each note entry, classify

For every entry parsed from the note's bibtex fence, decide one of
four outcomes by checking in order:

1. **Dedupe on author + year.** Extract the note entry's
   first-author surname and year:
   - First-author surname: the substring of `author` before the
     first `,` or ` and ` (BibTeX "Last, First" or "First Last"
     forms). Strip braces, accents (normalize to ASCII via
     Unicode NFKD then drop combining marks), trailing commas,
     and lowercase for comparison.
   - Year: the four-digit token in `year`.
   Scan existing `refs.bib` for an entry whose normalized
   first-author surname and year match. If found, confirm the
   match using DOI or title similarity:
   - If both entries have a DOI and they match → confirmed dedupe.
   - If DOIs differ → not a dedupe (different work). Proceed to
     step 2 (key collision).
   - If no DOI on either side, compare titles: lowercase both,
     strip punctuation and whitespace, compute token overlap. If
     ≥50% of tokens are shared → confirmed dedupe. Otherwise →
     different work, proceed to step 2.
   On confirmed dedupe:
   - Mark the note entry as **deduped**.
   - Propose the existing `refs.bib` key as the canonical one.
   - Run the field-conflict check (step 5). If a conflict is
     found, upgrade the outcome to **conflict**.
   - Do **not** append the note entry to `refs.bib`.

2. **Key collision on a different work.** If the note's key is
   not already used in `refs.bib`, skip this check. If it is used
   and step 1 did not match (i.e., same key but a different
   first-author-surname + year): suffix-bump the note's key with
   the lowest unused lowercase letter (`Smith2021` → `Smith2021a`
   → `Smith2021b` …), preserving the library's key style rules.
   Mark as **renamed**; continue to step 3.

3. **Truly new.** The note entry has no author+year match in
   `refs.bib` and its key does not collide with a different work.
   Mark as **new**. Keep the note's key (after any suffix-bump
   from step 2). Re-emit the entry using the project's detected
   field order, indentation, and spacing from step 3. Do not
   invent fields; preserve every field the note supplied.

4. **Malformed.** If the note entry has no `author`, no `year`,
   or no entry key, mark as **skipped** with the reason recorded.
   Do not attempt to merge it.

### 5. Conflict check (for deduped entries)

For every note entry matched to an existing `refs.bib` entry in
step 4.1, compare identifier fields:

- If both entries have a `doi` and the values differ (after
  lowercasing and stripping a `https://doi.org/` prefix), flag a
  **DOI conflict**.
- If both entries have a `url` and the canonicalized values
  differ (lowercase scheme+host, strip trailing slash, strip
  `utm_*` query params), flag a **URL conflict**.
- If the note supplies a `doi` or `url` that the existing entry
  lacks, record it as a **field-add suggestion** — do **not**
  write it into `refs.bib` in this skill (out of scope:
  modifying existing entries). Report it so the author can add
  it manually.

Conflicts are never auto-resolved. The existing `refs.bib` entry
stays intact; the note entry is not appended; the conflict is
reported with both values so the author can decide.

### 6. Append new entries

For each entry classified **new** (or **renamed**, which is still
new with a suffix-bumped key):

- Format the entry using the detected key style note (step 3) —
  if `zotero8` and the note minted an `author-year` key, keep the
  note's key but flag in the report that the project uses
  `zotero8` and the author may want to re-key manually; do **not**
  silently mint a zotero-style key (the skill has no key-minting
  authority, only dedup and format authority).
- Use the detected field order, indentation, and key–equals
  spacing.
- Append to the end of `refs.bib`, preceded by exactly one blank
  line if the file does not already end with one. Use `Edit` with
  the last existing entry as the anchor; do not rewrite the file
  with `Write`.
- If `--dry-run` is set, collect the would-be-appended text but
  do not modify the file.

### 7. Report

Print a summary to stdout in this exact shape:

```
bib-merge: {note-file} → {refs.bib}
  merged:   N entries appended
  deduped:  K entries matched existing keys (list: note-key → existing-key)
  renamed:  R entries suffix-bumped (list: old-key → new-key)
  conflicts: C entries flagged (list: key — field: note-value vs bib-value)
  skipped:  S entries malformed (list: key — reason)
  style:    key-style={detected}, field-order=[…], indent={n spaces|tab}
```

If `--dry-run`, prefix every line with `DRY-RUN: ` and state at
the end `DRY-RUN: refs.bib not modified`.

The report is the primary artefact the caller reads; it must be
concrete enough that an author can act on every conflict and
dedupe without re-parsing the files.

## Output

- Side effect (normal run): zero or more entries appended to
  `refs.bib`. No existing entry is edited, reordered, or removed.
  The note file is never modified.
- Side effect (`--dry-run`): none. Files unchanged.
- Stdout: the report from step 7.

## Test cases (documented; operator runs on PR review)

These are the four cases from ticket 0012. The operator runs them
manually on a sandbox note + `refs.bib` pair.

1. **Happy path — fresh note, no overlaps.** Construct a note
   with three Bibliography entries whose author+year tuples are
   absent from a sandbox `refs.bib`. Invoke the skill. Expect:
   exit 0; report shows `merged: 3`, `deduped: 0`, `renamed: 0`,
   `conflicts: 0`; `refs.bib` now ends with the three new
   entries, formatted in the project's detected style; no
   existing entry altered.

2. **Dedupe on author + year.** Construct a note with an entry
   `@article{Gotzens2019, author = {Götzens, F. and ...}, year =
   {2019}, ...}` when the sandbox `refs.bib` already contains
   `@article{LYGDCQCL, author = {Gotzens, Federico and ...}, year
   = {2019}, ...}` (note the accent and key difference). Invoke
   the skill. Expect: report shows `deduped: 1` with
   `Gotzens2019 → LYGDCQCL`; `refs.bib` unchanged (byte-for-byte
   the same as before the run); no duplicate added.

3. **Conflict on DOI mismatch.** Same as case 2, but the note's
   entry declares `doi = {10.1016/j.apenergy.2019.113783}` and
   the existing `LYGDCQCL` declares `doi =
   {10.1016/j.apenergy.2019.999999}`. Invoke the skill. Expect:
   report shows `conflicts: 1` listing the key and both DOI
   values; `deduped: 1` (the author+year match still holds);
   `refs.bib` unchanged; exit 0 (conflicts are reported, not
   fatal).

4. **Dry-run does not write.** Repeat case 1 with `--dry-run`.
   Expect: `refs.bib` byte-for-byte unchanged after the run; mtime
   unchanged; stdout is the dry-run-prefixed report ending with
   `DRY-RUN: refs.bib not modified`.

Each case confirms the invariants: the note file is never
modified; existing `refs.bib` entries are never rewritten; every
outcome appears in the report.

## Failure modes to avoid

- **Silently overwriting a conflicting DOI or URL.** If the note
  and `refs.bib` disagree on an identifier, the existing entry
  wins by inaction, and the disagreement is reported. Never
  mutate an existing entry.
- **Using `Write` on `refs.bib`.** Always append with `Edit`
  anchored to the last existing entry. A full rewrite would
  reorder or reformat entries the skill has no mandate to touch.
- **Matching first author by full name.** Middle initials,
  initials-vs-full-first-name, and accent encodings vary between
  BibTeX sources. Match on normalized surname (ASCII-fold,
  lowercase) + four-digit year only. When no DOI is available on
  either side, title similarity (≥50% token overlap) is the
  tiebreaker. Below the threshold, the entries are treated as
  different works and the note's key is suffix-bumped.
- **Minting keys the project's style does not use.** If the
  library is `zotero8`, this skill does not invent an 8-char key
  — it keeps the note's `AuthorYEAR` key and flags the style
  mismatch in the report. Key minting is outside the merge
  contract.
- **Creating `refs.bib` if it does not exist.** Aborting is
  correct; creating a new bibliography file is a project-setup
  decision the author owns.
- **Reordering or "tidying"** existing entries alphabetically,
  by type, or by field order. Appending is the only write
  operation.
- **Treating a renamed key as a silent change.** Every
  suffix-bump is reported so the author can update any
  `\cite{...}` calls that used the note's original key.

## Not in scope

- Removing `refs.bib` entries that no manuscript cites. Separate
  linter task.
- Fetching Crossref / OpenAlex metadata to fill missing fields.
  Enrichment is the author's job.
- Reordering `refs.bib` beyond appending new entries at the end.
- Editing existing `refs.bib` entries (adding a missing DOI,
  fixing a typo, merging a renamed-key cite). Reported as
  suggestions; the author does the edit.
- Modifying the note file in any way. The note is input-only.
- CI / pre-commit hook integration. This is a manual skill
  invoked after author approval.
