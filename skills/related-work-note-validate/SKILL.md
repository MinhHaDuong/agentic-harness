---
name: related-work-note-validate
description: Post-hoc validator for a `related-work-note` output. Scans the Bibliography for DOI/URL patterns, re-resolves each via WebFetch, flags entries with no identifier as unverifiable, and appends a provenance line to Methods. Does not rewrite the note. Prints a one-line verdict (PASS / WARN / FAIL).
disable-model-invocation: false
user-invocable: true
argument-hint: <note-file-path>
---

# Related-work-note validator

**Purpose.** The `related-work-note` skill specifies that every DOI
and URL in the Bibliography must resolve via `WebFetch` before the
note is emitted. This validator **enforces** that claim after the
fact: it scans the Bibliography for DOI and URL patterns,
re-resolves each one, flags entries that have neither identifier as
unverifiable, and records the result in the note's Methods section.
Specify (in `related-work-note`) + enforce (here).

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
- the `url = {...}` value, if present,
- the `eprint = {...}` value, if present (HAL or arXiv identifier).

Build a list of `(key, identifier, kind)` tuples where `kind` is
`doi`, `url`, or `eprint`. For entries with both a DOI and a URL, prefer the
DOI (resolve `https://doi.org/{DOI}`); the URL is a backup only if
the DOI check fails. An `eprint` value (HAL or arXiv URL/identifier)
is resolved the same way as a `url` entry. Entries with neither a DOI,
URL, nor eprint are classified as `unverifiable` — they cannot be resolved by this
validator and are flagged in the report (see step 4).

### 3. Resolve every identifier

For each `(key, identifier, kind)`:

- If `kind == doi`, `WebFetch` `https://doi.org/{DOI}` and record
  whether the fetch returned a 200 (or a 30x chain ending in 200).
- If `kind == url`, `WebFetch` the URL and record the same.
- Treat any non-2xx final status, DNS failure, or timeout as a
  failure. Record the entry key and the concrete reason
  (`404`, `timeout`, `DNS error`, etc.).

Serial fetches are acceptable. If a 429 (rate limit) response is
received, back off for 5 seconds and retry once before counting
the entry as failed. Stop after three consecutive network errors
and escalate: network failure is not a note failure.

### 4. Emit verdict

Classify every Bibliography entry into one of three buckets:

- **resolved** — fetched OK (2xx or 30x→2xx).
- **failed** — fetch returned non-2xx, DNS error, or timeout.
- **unverifiable** — entry has no DOI, URL, or eprint.

Verdict logic:

| Failed | Unverifiable | Verdict |
|--------|-------------|---------|
| 0      | 0           | `PASS`  |
| 0      | ≥1          | `WARN`  |
| ≥1     | any         | `FAIL`  |

### 5. Append the validator line to Methods — in place

Open the note file and append a single bullet to the end of the
`## Methods` section (before the next `##` header, or at EOF if
Methods is the last section). Do **not** rewrite any other part of
the file. The appended line uses one of these forms:

```
- **Validator (external check).** PASS — all N identifiers
  re-resolved on {YYYY-MM-DDThh:mmZ} by related-work-note-validate.
```

```
- **Validator (external check).** WARN — all resolvable
  identifiers OK, but {U} of {N} entries have no DOI or URL:
  {key1, key2, ...}. Checked {YYYY-MM-DDThh:mmZ}.
```

```
- **Validator (external check).** FAIL — {K} of {N} identifiers
  failed to re-resolve on {YYYY-MM-DDThh:mmZ}. Failing entries:
  {key1 (reason1), key2 (reason2), ...}. Unverifiable (no
  DOI/URL): {list, or 'none'}.
```

Use `Edit` with a unique anchor (the last line of Methods before
the next section) to append. Never overwrite the file with `Write`.

### 6. Print the one-line verdict

Print exactly one of:

- `PASS`
- `WARN: {U} of {N} entries have no DOI/URL`
- `FAIL: {K} entries unresolved, {U} unverifiable`

followed by the path of the note file that was annotated. Nothing
else goes to stdout — downstream tooling greps this line.

## Output

Side effect: one appended bullet in the note's `## Methods`
section.

Stdout: one verdict line (see step 6).

No other file is touched. No cited-work entry is edited. No
Bibliography entry is reformatted.

## Test cases (documented; operator runs on PR review)

1. **Clean pilot note → PASS.** Feed the 2026-04-17 pilot at
   `/tmp/skill-pilot/table-understanding-benchmarks.md` (or a
   regenerated equivalent). Every entry has a DOI or URL, and all
   resolve. Validator prints `PASS` and appends the PASS bullet
   to Methods.

2. **Note with a deliberately broken DOI → FAIL.** Edit the pilot
   to replace one DOI with `10.9999/definitely-not-real`.
   Validator prints `FAIL: 1 entries unresolved` and appends a
   FAIL bullet naming the bad entry key and the failure reason.

3. **Entry with no DOI or URL → WARN.** Edit the pilot to strip
   the `doi` and `url` fields from one BibTeX entry. Validator
   prints `WARN: 1 entries have no DOI/URL` and appends a WARN
   bullet listing the unverifiable entry key. All other entries
   still resolve normally.

Each case confirms the validator never touched cited-work bodies
or the Bibliography.

## Failure modes to avoid

- Rewriting the note with `Write`. Always use `Edit` to append a
  single bullet — preserving author edits between upstream
  emission and validator invocation.
- Silently skipping entries that lack a DOI or URL. These are
  `unverifiable` and must be flagged in the report.
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
