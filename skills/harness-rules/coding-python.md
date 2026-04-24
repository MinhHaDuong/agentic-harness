<!-- last-reviewed: 2026-04-23 -->
# Coding Rules

## Python (3.10+)

Style:
- Built-in generics: `list[str]`, `dict[str, int]`, `str | None`. Never `from typing import List, Dict, Tuple, Optional`.
- `X | Y` union syntax, not `Union[X, Y]`. No `from __future__ import annotations`.
- No ABC classes. Use Protocol for structural subtyping if needed.
- Type hints where they clarify intent. Skip where they add noise.
- Assertions at system boundaries. Trust internal code.

Script structure:
- **Every entry point gets argparse.** If `__name__ == "__main__"` exists, it gets an `ArgumentParser`.
- **Lean main() functions.** Delegate to well-named helpers.
- **No hardcoded paths.** Use `--output` and `--named-input` CLI params, with defaults from config.
- **No `sys.path` hacks.** Use proper packaging (`pyproject.toml`).
- **Logging, not print.** Use `logging` module.

Dependencies: **always `uv sync`** (never pip). `uv run python scripts/...` to execute.

## Testing

- Tests live in `tests/test_<module>.py`. A new script or changed behavior starts with a test.
- `make check-fast`: unit tests + lint, < 30 s — run during development.
- `make check`: full suite including integration + slow tests — run before opening a PR.

| Marker | Meaning | Excluded from |
|--------|---------|---------------|
| *(none)* | Unit test — pure logic, no subprocess, no sleep | — |
| `@pytest.mark.integration` | Spawns subprocesses or uses sleep-based timing | `check-fast` |
| `@pytest.mark.slow` | Requires network access or real data | `check-fast` |

When writing new tests:
- CLI flag presence: check via source inspection (`open().read()` + string match), not subprocess `--help`.
- Tests using `subprocess.run()` or `time.sleep()`: mark `@pytest.mark.integration`.
- Tests needing heavy modules only for `inspect.getsource()`: read the file directly instead.

## Build (Make)

- **One output per rule.** Each target should produce a known file so timestamps work.
- **Sentinel stamps for dynamic outputs.** Use a stamp file when a script produces data-dependent filenames.
- **No `.PHONY` for real work.** Use `.PHONY` only for aliases.
- **No hand-curated data in the pipeline.** Every CSV/tex file referenced by slides or report must have a Makefile target that generates it from `measurements.jsonl` or another tracked source.
- **Split the build by workpackage.** Analysis (Python/R, data access) and writing (LaTeX, Quarto) workpackages live in separate Makefiles. A writing-side build must produce the manuscript from handoff artifacts alone — no `uv run`, no data fetch. Enables clean-room builds and enforces the artifact discipline in [git.md](./git.md).
