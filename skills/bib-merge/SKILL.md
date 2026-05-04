---
name: bib-merge
description: Merge approved Bibliography entries from a related-work-note into the project's refs.bib. Dedupes, flags conflicts, appends new entries. Never rewrites existing entries.
disable-model-invocation: false
user-invocable: true
argument-hint: <note-file-path> [<refs-bib-path>] [--dry-run]
---

# Bibliography merge

Merge the ```bibtex fence from a `related-work-note`'s Bibliography
section into a local `refs.bib`. Dedupe against existing entries,
flag conflicts, append new ones, report everything.

## Constraints (non-obvious)

- **Append-only.** The script appends entries; never rewrites or
  reorders existing entries. If refs.bib doesn't exist, script
  aborts with exit 1 — that's a project-setup decision.
- **Never mutate existing entries.** If the note has a field the
  existing entry lacks, report it as a suggestion. Don't write it.
- **Dedupe on author+year, confirm with DOI or title.**
  Matching DOI → SKIPPED. Differing DOI → different work, suffix-bump
  the key (RENAMED). No DOI → judge by title similarity (Jaccard ≥ 0.8).
- **Report suffix-bumps.** Every renamed key must be reported so
  the author can update `\cite{}` calls.
- **Note file is read-only.** Never modify it.
- **`--dry-run`** runs the full logic, prefixes report with
  `DRY-RUN:`, does not write.
- **Local .bib is staging.** The canonical library is Zotero. At
  manuscript submission, the author imports refs.bib into Zotero
  and attaches PDFs. This skill does not automate that step
  (see ticket 0013).

## Input

1. Note file path (required) — must have `## Bibliography` with a
   ```bibtex fence. The script auto-extracts the fence.
2. refs.bib path (optional) — default `report/refs.bib` if it exists.
3. `--dry-run` flag (optional).

## Steps

**Step 1 — resolve refs.bib path (if not provided)**

If the user did not provide a refs.bib path, check whether
`report/refs.bib` exists in the current project. If it does, use it.
If neither exists, abort with: `ERROR: no refs.bib found`.

**Step 2 — run the deduplication script (one Bash call)**

```
python3 ~/.claude/scripts/bib-merge.py <note-file> <refs.bib> [--dry-run]
```

The script:
- Extracts the ```bibtex fence from the note file automatically
- Parses all entries from both the fence and refs.bib
- Deduplicates (author+year primary key; DOI or title confirmation)
- Appends non-duplicate entries to refs.bib (unless --dry-run)
- Prints a report to stdout

**Step 3 — relay the report**

Print the script's stdout verbatim as the skill output.

## Report format (from script)

```
bib-merge: {note-file} → {refs.bib}
  added:    N
  skipped:  K  (duplicates)
  renamed:  R  (key collisions)
  errors:   E  (malformed entries)
[ADDED] @key
[SKIPPED] @key  (duplicate of @existingkey)
[RENAMED->newkey] @oldkey
```
