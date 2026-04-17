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

- **Append-only.** Use `Edit` anchored to the last entry to append.
  Never rewrite, reorder, or reformat existing entries. If refs.bib
  is empty, use `Write` for the first entry.
- **Never create refs.bib.** If it doesn't exist, abort. That's a
  project-setup decision.
- **Never mutate existing entries.** If the note has a field the
  existing entry lacks (e.g., a DOI), report it as a suggestion.
  Don't write it.
- **Dedupe on author+year, confirm with DOI or title.** If DOIs
  match → same work. If DOIs differ → same work, metadata conflict
  (report both, don't append). If no DOI on either side → judge by
  title similarity. Different titles → different work, suffix-bump
  the key.
- **Report suffix-bumps.** Every renamed key must be reported so
  the author can update `\cite{}` calls.
- **Match the library's formatting style** (indentation, field
  order, key-equals spacing) for new entries. Don't mint keys in a
  style the library doesn't use — flag the mismatch instead.
- **Note file is read-only.** Never modify it.
- **`--dry-run`** runs the full logic, prefixes report with
  `DRY-RUN:`, does not write.
- **Local .bib is staging.** The canonical library is Zotero. At
  manuscript submission, the author imports refs.bib into Zotero
  and attaches PDFs. This skill does not automate that step
  (see ticket 0013).

## Input

1. Note file path (required) — must have `## Bibliography` with a
   ```bibtex fence.
2. refs.bib path (optional) — default `report/refs.bib` if it exists.
3. `--dry-run` flag (optional).

## Report format

```
bib-merge: {note-file} → {refs.bib}
  merged:      N entries appended
  deduped:     K (list: note-key → existing-key)
  renamed:     R (list: old-key → new-key)
  conflicts:   C (list: key — field: note-value vs bib-value)
  suggestions: F field-adds (list: key — field: value)
  skipped:     S malformed (list: key — reason)
```
