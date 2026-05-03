"""Tests for scripts/fewer-permission-prompts-helper.py.

The helper invokes the `claude` CLI; here we shim it with a fake `claude`
on PATH so the tests are hermetic and never touch the real CLI.
"""

import os
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

HELPER = Path(__file__).parent.parent / "scripts" / "fewer-permission-prompts-helper.py"


def _make_fake_claude(bin_dir: Path, *, stdout: str = "diff content\n", rc: int = 0) -> Path:
    """Create a tiny shell stub that mimics the `claude` CLI."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake = bin_dir / "claude"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s' {stdout!r}\n"
        f"exit {rc}\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return fake


def _run_helper(project_path: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(HELPER), str(project_path)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_helper_writes_diff_file(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    _make_fake_claude(bin_dir, stdout="proposed allowlist diff\n")
    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "proj"
    project.mkdir()

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["HOME"] = str(home)

    result = _run_helper(project, env)
    assert result.returncode == 0, result.stderr

    diffs_dir = home / ".claude" / "telemetry" / "permission-diffs"
    assert diffs_dir.is_dir()
    today = datetime.now().strftime("%Y-%m-%d")
    diff_path = diffs_dir / f"{today}.diff"
    assert diff_path.exists()
    assert "proposed allowlist diff" in diff_path.read_text()


def test_helper_does_not_crash_when_claude_missing(tmp_path):
    """If the `claude` CLI is unavailable, helper must exit 0 with a stub diff."""
    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "proj"
    project.mkdir()

    env = os.environ.copy()
    # Strip PATH so `claude` cannot be found.
    env["PATH"] = "/nonexistent"
    env["HOME"] = str(home)

    result = _run_helper(project, env)
    assert result.returncode == 0, (
        f"helper must not crash when claude missing; got rc={result.returncode}\n"
        f"stderr={result.stderr}"
    )

    diffs_dir = home / ".claude" / "telemetry" / "permission-diffs"
    today = datetime.now().strftime("%Y-%m-%d")
    diff_path = diffs_dir / f"{today}.diff"
    assert diff_path.exists()
    # Stub diff should mention that the CLI was unavailable.
    body = diff_path.read_text()
    assert body.startswith("#") or "unavailable" in body.lower() or "claude" in body.lower()


def test_helper_appends_when_run_twice_same_day(tmp_path):
    bin_dir = tmp_path / "bin"
    _make_fake_claude(bin_dir, stdout="first\n")
    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "proj"
    project.mkdir()

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["HOME"] = str(home)

    r1 = _run_helper(project, env)
    assert r1.returncode == 0, r1.stderr

    # Second invocation on the same day should append, not clobber.
    _make_fake_claude(bin_dir, stdout="second\n")
    r2 = _run_helper(project, env)
    assert r2.returncode == 0, r2.stderr

    today = datetime.now().strftime("%Y-%m-%d")
    diff_path = home / ".claude" / "telemetry" / "permission-diffs" / f"{today}.diff"
    body = diff_path.read_text()
    assert "first" in body
    assert "second" in body


def test_helper_requires_project_arg(tmp_path):
    env = os.environ.copy()
    env["HOME"] = str(tmp_path / "home")
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(HELPER)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
