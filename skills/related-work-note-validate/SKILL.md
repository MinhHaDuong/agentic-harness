---
name: related-work-note-validate
description: Post-hoc validator for a `related-work-note` output. Re-resolves every DOI/URL in the note's Bibliography via WebFetch, compares against the note's own "Identifier resolution" claim in Methods, and appends a validator-provenance line in place. Does not rewrite the note. Prints a one-line verdict (PASS / FAIL / MISSING).
disable-model-invocation: false
user-invocable: true
argument-hint: <note-file-path>
---

# Related-work-note validator

**Purpose.** The `related-work-note` skill specifies that every DOI
and URL in the Bibliography must resolve via `WebFetch` before the
note is emitted. This validator **enforces** that claim after the
fact: it re-resolves every identifier in the note's Bibliography,
compares its own result against the note's Methods "Identifier
resolution" line, and records the external check alongside the
LLM-side claim. Specify (in `related-work-note`) + enforce (here).

**Scope.** One invocation = one note file. The validator touches
only the note's Methods section (a single appended line). It never
edits the cited-work bodies, the bibliography, or any other file.

## When to use

- Immediately after a `related-work-note` run, before handing the
  note to the author.
- When auditing an older note whose freshness or provenance is in
  doubt.
- As a manual spot-check during peer-review rebuttal prep.

This is **not** a CI hook. It is a manual skill invoked by the
operator (or the orchestrator) after note generation. Hook
integration is out of scope (see ticket 0011).

## Input

One positional argument: the path to a note file previously emitted
by the `related-work-note` skill.

If the path is missing, unreadable, or the file does not have the
expected `## Bibliography` and `## Methods` sections, abort with a
one-line error — do not guess or partially validate.

## Steps

### 1. Read the note

Use `Read` on the caller-supplied path. Confirm the file contains a
`## Bibliography` section and a `## Methods` section. If either is
absent, print `MISSING: note structure invalid` and stop — this is
distinct from the resolution-line MISSING verdict and signals the
file is not a `related-work-note` output at all.

### 2. Extract identifiers from the Bibliography

Parse the Bibliography section (BibTeX-style entries). For each
entry, collect:

- the entry key (e.g., `AuthorYEAR`),
- the `doi = {...}` value, if present,
- the `url = {...}` value, if present.

Build a list of `(key, identifier, kind)` tuples where `kind` is
`doi` or `url`. For entries with both a DOI and a URL, prefer the
DOI (resolve `https://doi.org/{DOI}`); the URL is a backup only if
the DOI check fails. Entries with neither a DOI nor a URL count as
failures with reason `no identifier`.

### 3. Resolve every identifier

For each `(key, identifier, kind)`:

- If `kind == doi`, `WebFetch` `https://doi.org/{DOI}` and record
  whether the fetch returned a 200 (or a 30x chain ending in 200).
- If `kind == url`, `WebFetch` the URL and record the same.
- Treat any non-2xx final status, DNS failure, or timeout as a
  failure. Record the entry key and the concrete reason
  (`404`, `timeout`, `DNS error`, etc.).

Do not rate-limit aggressively — academic DOIs tolerate serial
fetches — but do stop after three consecutive network errors and
escalate: network failure is not a note failure.

### 4. Parse the note's resolution claim

Scan the `## Methods` section for the line the upstream skill was
supposed to write. The canonical form is:

```
- **Identifier resolution.** "All N bibliography entries were
  fetched on {YYYY-MM-DD} and returned a 200 (or 30x to a 200).
  Entries that failed to resolve: {list, or 'none'}."
```

Extract:

- the declared count `N`,
- the declared failure list (empty / "none" / a list of keys).

If no line matching `Identifier resolution` is present in Methods,
the claim is missing — go to step 5 with verdict `MISSING`.

### 5. Compare and emit verdict

Three cases:

| Note's claim                         | Validator result | Verdict  |
|--------------------------------------|------------------|----------|
| "All N resolved" (N matches, none failed) | all fetched OK | `PASS` |
| "All N resolved" (or similar)        | ≥1 fetch failed  | `FAIL`   |
| No "Identifier resolution" line      | (any)            | `MISSING` |

`N` mismatch between the note's declared count and the actual
number of Bibliography entries is also a `FAIL` — record as
`count mismatch: note claims N, bibliography has M`.

### 6. Append the validator line to Methods — in place

Open the note file and append a single bullet to the end of the
`## Methods` section (before the next `##` header, or at EOF if
Methods is the last section). Do **not** rewrite any other part of
the file. The appended line uses one of these forms:

```
- **Validator (external check).** PASS — all N identifiers
  re-resolved on {YYYY-MM-DDThh:mmZ} by related-work-note-validate.
```

```
- **Validator (external check).** FAIL — {K} of {N} identifiers
  failed to re-resolve on {YYYY-MM-DDThh:mmZ}. Failing entries:
  {key1 (reason1), key2 (reason2), ...}. Caller should re-run the
  upstream skill or fix the note manually.
```

```
- **Validator (external check).** MISSING — note has no
  "Identifier resolution" line in Methods; upstream skill
  misbehaved. Validator re-resolved {N} Bibliography entries:
  {K} failures. Checked {YYYY-MM-DDThh:mmZ}.
```

Use `Edit` with a unique anchor (the last line of Methods before
the next section) to append. Never overwrite the file with `Write`.

### 7. Print the one-line verdict

Print exactly one of:

- `PASS`
- `FAIL: {N} entries unresolved`
- `MISSING: no resolution line in note`

followed by the path of the note file that was annotated. Nothing
else goes to stdout — downstream tooling greps this line.

## Output

Side effect: one appended bullet in the note's `## Methods`
section.

Stdout: one verdict line (see step 7).

No other file is touched. No cited-work entry is edited. No
Bibliography entry is reformatted.

## Test cases (documented; operator runs on PR review)

1. **Clean pilot note → PASS.** Feed the 2026-04-17 pilot at
   `/tmp/skill-pilot/table-understanding-benchmarks.md` (or a
   regenerated equivalent). Every DOI/URL resolves. Methods
   contains the expected "Identifier resolution" line. Validator
   prints `PASS` and appends the PASS bullet to Methods.

2. **Note with a deliberately broken DOI → FAIL.** Edit the pilot
   to replace one DOI with `10.9999/definitely-not-real`. The
   note's own Methods still claims "all N resolved". Validator
   prints `FAIL: 1 entries unresolved` and appends a FAIL bullet
   naming the bad entry key and the failure reason.

3. **Note missing the resolution line → MISSING.** Edit the pilot
   to delete the `**Identifier resolution.**` bullet from Methods.
   Validator prints `MISSING: no resolution line in note` and
   appends a MISSING bullet to Methods (including the validator's
   own re-resolution summary, so the author still sees the truth).

Each case confirms the validator never touched cited-work bodies
or the Bibliography.

## Failure modes to avoid

- Rewriting the note with `Write`. Always use `Edit` to append a
  single bullet — preserving author edits between upstream
  emission and validator invocation.
- Silently passing when the bibliography count differs from the
  note's declared `N`. Count mismatch is a `FAIL`.
- Treating a network glitch as a citation failure. Three
  consecutive network errors → abort with an escalation message,
  not a `FAIL` verdict.
- Interpreting the note's prose (Relevance, History, Cited works).
  The validator is mechanical: Bibliography identifiers in,
  Methods annotation out.
- Fetching Crossref metadata or otherwise "deepening" the check.
  200 OK is the bar. Semantic validation is the author's job.

## Not in scope

- CI or pre-commit hook integration. Separate decision.
- Editing cited-work content, Bibliography entries, or any other
  section than Methods.
- Crossref / OpenAlex metadata enrichment. Resolution is `200 OK`
  only.
- Re-running the upstream `related-work-note` skill on FAIL. The
  caller decides whether to re-run or fix manually.
