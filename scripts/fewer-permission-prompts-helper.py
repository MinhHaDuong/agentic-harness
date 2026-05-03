#!/usr/bin/env python3
"""fewer-permission-prompts-helper.py — emit a weekly allowlist-diff proposal.

Spawns a non-interactive Claude Code session that invokes the Anthropic-shipped
skill `/fewer-permission-prompts`. Writes the captured stdout (the proposed
diff) to `~/.claude/telemetry/permission-diffs/<YYYY-MM-DD>.diff`. Diffs are
NEVER auto-applied — they are surfaced read-only by `nightbeat-report.py`.

Known caveat: bug `anthropics/claude-code#51057` strips environment-variable
prefixes during extraction, so commands like
    TEST_DATABASE_URL=... uv run pytest
are missed. Verify diffs by hand before applying.

Usage:
    fewer-permission-prompts-helper.py <project-path>

Exit codes:
    0   — diff (or stub diff) written successfully
    2   — usage error (missing project arg)

Failure modes that fall back gracefully (still exit 0):
    - `claude` CLI not on PATH                 → write stub-comment diff
    - non-interactive flag rejected            → fall back to piping `\n` to stdin
    - subprocess.TimeoutExpired                → write stub diff with timeout note

This script must never crash the calling beat — see scripts/beat.py
`_prune_permissions`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.tracebacklimit = 1


HARNESS_DIR = Path.home() / ".claude"
DIFF_DIR = HARNESS_DIR / "telemetry" / "permission-diffs"

# Cap on the spawned `claude` invocation. The wrapper above (`beat.py`)
# already caps the helper at 10 minutes; this is the inner soft limit.
CLAUDE_TIMEOUT_S = 8 * 60

PROMPT_SLASH = "/fewer-permission-prompts"


def _today_diff_path() -> Path:
    return DIFF_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.diff"


def _ensure_dirs() -> None:
    DIFF_DIR.mkdir(parents=True, exist_ok=True)


def _append_diff(content: str, *, header: str | None = None) -> Path:
    path = _today_diff_path()
    pieces: list[str] = []
    if header:
        pieces.append(f"# {header}\n")
    if content and not content.endswith("\n"):
        content = content + "\n"
    pieces.append(content)
    with path.open("a") as fh:
        fh.write("".join(pieces))
    return path


def _claude_available() -> bool:
    return shutil.which("claude") is not None


def _spawn_claude(project: Path) -> tuple[int, str, str]:
    """Try non-interactive first; fall back to piping stdin if needed.

    Returns (returncode, stdout, stderr). Never raises for normal failure
    modes (timeout, missing CLI) — the caller handles fallbacks.
    """
    # First attempt: --non-interactive (preferred path).
    try:
        proc = subprocess.run(  # noqa: S603, S607
            [
                "claude",
                "--non-interactive",
                "-p",
                PROMPT_SLASH,
                "--output-format",
                "stream-json",
            ],
            cwd=str(project),
            capture_output=True,
            text=True,
            check=False,
            timeout=CLAUDE_TIMEOUT_S,
        )
        # Older / current `claude` may not know `--non-interactive`. If it
        # exited non-zero AND its stderr suggests the flag was rejected,
        # fall through to the stdin fallback.
        if proc.returncode == 0:
            return proc.returncode, proc.stdout, proc.stderr
        stderr_lc = (proc.stderr or "").lower()
        unknown_flag = any(
            phrase in stderr_lc
            for phrase in (
                "non-interactive",
                "unknown",
                "unrecognized",
                "unrecognised",
                "no such option",
                "invalid option",
                "invalid argument",
            )
        )
        if not unknown_flag:
            return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or "", f"timeout after {CLAUDE_TIMEOUT_S}s"
    except FileNotFoundError:
        return 127, "", "claude CLI not found"

    # Fallback: pipe a confirm-no `\n` to stdin.
    try:
        proc = subprocess.run(  # noqa: S603, S607
            ["claude", "-p", PROMPT_SLASH],
            cwd=str(project),
            input="\n",
            capture_output=True,
            text=True,
            check=False,
            timeout=CLAUDE_TIMEOUT_S,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or "", f"timeout after {CLAUDE_TIMEOUT_S}s"
    except FileNotFoundError:
        return 127, "", "claude CLI not found"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "usage: fewer-permission-prompts-helper.py <project-path>",
            file=sys.stderr,
        )
        return 2

    project = Path(argv[1]).expanduser()
    _ensure_dirs()
    today = datetime.now().strftime("%Y-%m-%d")

    if not _claude_available():
        path = _append_diff(
            "",
            header=(
                f"{today} — claude CLI unavailable on this host;"
                " no diff produced. See ticket 0043."
            ),
        )
        print(path)
        return 0

    rc, stdout, stderr = _spawn_claude(project)
    if rc == 0 and stdout.strip():
        path = _append_diff(
            stdout,
            header=f"{today} — /fewer-permission-prompts (project: {project})",
        )
    elif rc == 124:
        path = _append_diff(
            "",
            header=(
                f"{today} — /fewer-permission-prompts timed out for {project}."
                " Skipped this week."
            ),
        )
    else:
        path = _append_diff(
            stderr or "(no output)",
            header=(
                f"{today} — /fewer-permission-prompts rc={rc} for {project};"
                " see stderr below."
            ),
        )

    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
