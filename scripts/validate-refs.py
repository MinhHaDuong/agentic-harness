#!/usr/bin/env python3
"""validate-refs.py — resolve every DOI/URL/eprint in a related-work-note.

Usage:
    python3 validate-refs.py <note-file>

Parses the ## Bibliography section, extracts doi/url/eprint+eprinttype
from BibTeX entries, and fetches each identifier via HTTP.

Per-entry output goes to stderr:
    [OK|WARN|FAIL] {key}: {resolved-url} ({status})

Final verdict goes to stdout (single line, downstream-greppable):
    PASS — {N} entries resolved
    WARN: {U} of {N} entries have no DOI/URL — {note-path}
    FAIL: {K} fetch failures — {note-path}
    ERROR: network issues ({K} consecutive failures) — {note-path}

Exit codes:
    0   PASS or WARN (unverifiable entries but no fetch failures)
    1   FAIL (at least one fetch returned non-200)
    2   ERROR (persistent network problems — escalate, do not mark as FAIL)
    3   usage or parse error (missing section, malformed input)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIMEOUT_S = 10
MAX_RETRIES = 3
CONSECUTIVE_ERRORS_THRESHOLD = 3

DOI_BASE = "https://doi.org/"
ARXIV_BASE = "https://arxiv.org/abs/"
HAL_BASE = "https://hal.science/"

HEADERS = {
    "User-Agent": "validate-refs/1.0 (related-work-note checker; mailto:minh.haduong@gmail.com)",
}


# ---------------------------------------------------------------------------
# BibTeX parsing
# ---------------------------------------------------------------------------


def _extract_bibliography_block(text: str) -> str:
    """Return the text between ## Bibliography and the next ## heading (or EOF)."""
    m = re.search(
        r"^## Bibliography\s*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL
    )
    if not m:
        return ""
    return m.group(1)


def _split_entries(bib_block: str) -> list[tuple[str, str]]:
    """Split BibTeX block into list of (key, raw_entry) pairs."""
    entries = []
    # Match @type{key, ... }
    for m in re.finditer(
        r"@\w+\{([^,\s]+)\s*,([^@]*?)^\}", bib_block, re.MULTILINE | re.DOTALL
    ):
        key = m.group(1).strip()
        body = m.group(2)
        entries.append((key, body))
    return entries


def _field(body: str, name: str) -> str | None:
    """Extract a BibTeX field value from an entry body (single-line or multi-line)."""
    # Handles: field = {value}, field = "value", field = value,
    pattern = rf"^\s*{name}\s*=\s*[{{\"']?(.*?)[}}\"']?\s*[,\n]"
    m = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
    if m:
        return m.group(1).strip().rstrip("}")
    return None


def _build_url(key: str, body: str) -> tuple[str | None, str]:
    """Return (url_to_fetch, identifier_type) for a BibTeX entry body.

    Priority: doi > eprint (typed) > url. Returns (None, "none") if no
    identifier found.
    """
    doi = _field(body, "doi")
    if doi:
        doi = doi.strip()
        for prefix in (
            "https://doi.org/",
            "http://doi.org/",
            "http://dx.doi.org/",
            "doi:",
        ):
            if doi.lower().startswith(prefix):
                doi = doi[len(prefix) :]
                break
        return DOI_BASE + doi, "doi"

    eprint = _field(body, "eprint")
    eprinttype = (_field(body, "eprinttype") or "").lower()
    if eprint:
        if eprinttype == "arxiv":
            return ARXIV_BASE + eprint, "arxiv"
        elif eprinttype == "hal":
            return HAL_BASE + eprint, "hal"
        else:
            # Unknown eprinttype — try to guess from format
            if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", eprint):
                return ARXIV_BASE + eprint, "arxiv"
            elif re.match(r"^hal-\d+", eprint):
                return HAL_BASE + eprint, "hal"
            # Emit as-is; caller will mark WARN
            return None, "none"

    url = _field(body, "url")
    if url:
        return url, "url"

    return None, "none"


# ---------------------------------------------------------------------------
# HTTP fetch
# ---------------------------------------------------------------------------


def _fetch(url: str) -> tuple[int | None, str, bool]:
    """Fetch url, following redirects.

    Returns (status_code, final_url, is_connection_error).
    is_connection_error=True means a network-level failure (not HTTP error).
    """
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers=HEADERS, timeout=TIMEOUT_S, allow_redirects=True
            )
            return resp.status_code, resp.url, False
        except requests.exceptions.ConnectionError:
            if attempt == MAX_RETRIES - 1:
                return None, url, True
        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES - 1:
                return None, url, True
        except requests.exceptions.RequestException:
            return None, url, True
    return None, url, True  # unreachable but satisfies type checker


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate-refs.py <note-file>", file=sys.stderr)
        return 3

    note_path = Path(argv[1])
    if not note_path.exists():
        print(f"error: file not found: {note_path}", file=sys.stderr)
        return 3

    text = note_path.read_text(encoding="utf-8")

    bib_block = _extract_bibliography_block(text)
    if not bib_block.strip():
        print(
            f"error: no ## Bibliography section found in {note_path}", file=sys.stderr
        )
        return 3

    if "## Methods" not in text:
        print(f"error: no ## Methods section found in {note_path}", file=sys.stderr)
        return 3

    entries = _split_entries(bib_block)
    if not entries:
        print(f"WARN: 0 of 0 entries have no DOI/URL — {note_path}")
        return 0

    n_total = len(entries)
    n_warn = 0  # entries with no identifier (unverifiable)
    n_fail = 0  # entries with fetch failures
    n_conn_err = 0  # consecutive connection errors

    for key, body in entries:
        url, id_type = _build_url(key, body)

        if url is None:
            n_warn += 1
            n_conn_err = 0
            print(f"[WARN] {key}: no identifier (unverifiable)", file=sys.stderr)
            continue

        status, final_url, is_conn_err = _fetch(url)

        if is_conn_err:
            n_conn_err += 1
            if n_conn_err >= CONSECUTIVE_ERRORS_THRESHOLD:
                print(
                    f"[ERROR] {key}: connection error after {MAX_RETRIES} retries — {url}",
                    file=sys.stderr,
                )
                print(
                    f"ERROR: network issues ({n_conn_err} consecutive failures) — {note_path}"
                )
                return 2
            print(f"[FAIL] {key}: connection error — {url}", file=sys.stderr)
            n_fail += 1
        elif status and status < 400:
            n_conn_err = 0
            print(f"[OK] {key}: {final_url} ({status})", file=sys.stderr)
        else:
            n_conn_err = 0
            print(f"[FAIL] {key}: {final_url} ({status})", file=sys.stderr)
            n_fail += 1

    if n_fail > 0:
        print(f"FAIL: {n_fail} fetch failures — {note_path}")
        return 1
    elif n_warn > 0:
        print(f"WARN: {n_warn} of {n_total} entries have no DOI/URL — {note_path}")
        return 0
    else:
        print(f"PASS — {n_total} entries resolved")
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
