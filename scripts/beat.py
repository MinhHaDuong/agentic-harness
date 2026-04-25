#!/usr/bin/env python3
"""beat.py — autonomous project maintenance orchestrator.

Replaces beat.sh + skills/beat/SKILL.md.
Control flow: [housekeeping] → pick-ticket → [orchestrator]

Environment:
  BEAT_DRY_RUN=1   Print intended sequence without invoking Claude.
"""

import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import TextIOBase
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────────

HARNESS_DIR = Path.home() / ".claude"

PROJECTS: list[Path] = [
    Path.home() / "aedist-technical-report",
    Path.home() / "cadens",
    Path.home() / "Climate_finance",
    Path.home() / "fuzzy-corpus",
]

LOGDIR = HARNESS_DIR / "logs" / "nightbeat"
COUNTER_FILE = LOGDIR / ".run-counter"

_runtime_dir = os.environ.get("RUNTIME_DIRECTORY") or os.environ.get("XDG_RUNTIME_DIR")
LOCKFILE = (
    Path(_runtime_dir) / "nightbeat.lock"
    if _runtime_dir
    else Path.home() / ".cache" / "nightbeat.lock"
)

HOUSEKEEPING_INTERVAL_S: int = 12 * 3600
HOUSEKEEPING_TIMEOUT_S: int = 10 * 60
PICK_TICKET_TIMEOUT_S: int = 8 * 60
ORCHESTRATOR_TIMEOUT_S: int = 30 * 60
CRASH_RECOVERY_WINDOW_S: int = 55 * 60
LOG_RETAIN_COUNT: int = 60
TIMEOUT_EXIT_CODE: int = 124  # matches bash `timeout` convention

BUDGET_HOUSEKEEPING: float = 0.25
BUDGET_PICK_TICKET: float = 0.50
BUDGET_ORCHESTRATOR: float = 5.00

DRY_RUN: bool = os.environ.get("BEAT_DRY_RUN") == "1"


# ── Process-wide state (shared with signal handler) ───────────────────────────


@dataclass
class _State:
    beat_start: float = 0.0
    project: Path | None = None
    current_proc: subprocess.Popen | None = field(default=None, repr=False)
    log_fh: TextIOBase | None = field(default=None, repr=False)
    final_written: bool = False


_state = _State()


# ── Logging ────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    line = msg if msg.endswith("\n") else msg + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    if _state.log_fh is not None:
        try:
            _state.log_fh.write(line)
            _state.log_fh.flush()
        except OSError:
            pass


# ── beat-log.jsonl management ─────────────────────────────────────────────────


def _beat_log_path(project: Path) -> Path:
    return project / "beat-log.jsonl"


def append_beat_log(project: Path, record: dict) -> None:
    """Append one compact-JSON record; no-op in dry-run mode."""
    if DRY_RUN:
        return
    path = _beat_log_path(project)
    with path.open("a") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")


def finalize_beat_log(project: Path, record: dict) -> None:
    """Write terminal spin-down record, replacing any trailing in_progress.

    Idempotent via _state.final_written; no-op in dry-run mode.
    """
    if _state.final_written or DRY_RUN:
        return
    _state.final_written = True

    path = _beat_log_path(project)
    if not path.exists():
        append_beat_log(project, record)
        return

    lines = path.read_text().splitlines()
    while lines:
        try:
            if json.loads(lines[-1]).get("outcome") == "in_progress":
                lines.pop()
                continue
        except (json.JSONDecodeError, AttributeError):
            pass
        break

    lines.append(json.dumps(record, separators=(",", ":")))
    path.write_text("\n".join(lines) + "\n")


def read_last_beat_record(project: Path) -> dict | None:
    """Return the last record in beat-log.jsonl, handling pretty-printed JSON."""
    path = _beat_log_path(project)
    if not path.exists() or path.stat().st_size == 0:
        return None
    result = subprocess.run(  # noqa: S603
        ["jq", "-s", "last"],
        input=path.read_text(),
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        obj = json.loads(result.stdout)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


# ── Signal handling ────────────────────────────────────────────────────────────


def _on_sigterm(_signum: int, _frame: object) -> None:
    elapsed = int(time.monotonic() - _state.beat_start)
    proc = _state.current_proc
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    if _state.project is not None:
        finalize_beat_log(
            _state.project,
            {
                "last_run_at": _now_iso(),
                "ticket_id": None,
                "branch": None,
                "PR": None,
                "outcome": "aborted",
                "diagnostics": "systemd SIGTERM — beat exceeded time budget",
                "duration_s": elapsed,
            },
        )
    _log(f"=== beat SIGTERM elapsed={elapsed}s {_now_iso()} ===")
    sys.exit(143)


# ── Housekeeping check ─────────────────────────────────────────────────────────


def housekeeping_needed(project: Path) -> bool:
    """Return True when the last housekeeping git commit is older than the interval."""
    result = subprocess.run(  # noqa: S603
        ["git", "log", "--grep=housekeeping", "-1", "--format=%ct"],
        capture_output=True,
        text=True,
        check=False,
        cwd=project,
    )
    raw = result.stdout.strip()
    if not raw:
        return True
    try:
        return (time.time() - int(raw)) > HOUSEKEEPING_INTERVAL_S
    except ValueError:
        return True


# ── Pick-ticket output parser ─────────────────────────────────────────────────


def parse_pick(result_text: str) -> str | None:
    """Return 4-digit ticket ID from PICK: line, or None for IDLE / no match."""
    if re.search(r"\bIDLE\b", result_text, re.IGNORECASE):
        return None
    m = re.search(r"\bPICK:\s*(\d{4})\b", result_text)
    return m.group(1) if m else None


# ── Claude subprocess ──────────────────────────────────────────────────────────


def _claude_argv(skill: str, budget: float) -> list[str]:
    return [
        "claude",
        "--print",
        "--verbose",
        "--output-format",
        "stream-json",
        "--permission-mode",
        "bypassPermissions",
        "--no-session-persistence",
        "--max-budget-usd",
        f"{budget:.2f}",
        "--model",
        "sonnet",
        "--settings",
        str(HARNESS_DIR / "scripts" / "beat-settings.json"),
        "--add-dir",
        str(HARNESS_DIR),
        "--add-dir",
        ".",
        "-p",
        skill,
    ]


def run_skill(
    skill: str, *, budget: float, timeout_s: int, cwd: Path
) -> tuple[int, str]:
    """Invoke a Claude skill; return (exit_code, last_result_text).

    Streams stdout line-by-line for live logging.
    Returns exit_code=TIMEOUT_EXIT_CODE on timeout.
    """
    argv = _claude_argv(skill, budget)

    if DRY_RUN:
        _log(f"[dry-run] {' '.join(argv)}")
        if "pick-ticket" in skill:
            return 0, "PICK: 9999"
        return 0, "(dry-run ok)"

    env = {**os.environ, "CLAUDE_NIGHT_SWEEP": "1"}
    proc = subprocess.Popen(  # noqa: S603
        argv,
        stdout=subprocess.PIPE,
        stderr=None,  # inherit → systemd journal
        text=True,
        bufsize=1,
        cwd=cwd,
        env=env,
    )
    _state.current_proc = proc

    stdout_lines: list[str] = []

    def _reader() -> None:
        if proc.stdout is None:
            return
        for raw in proc.stdout:
            line = raw.rstrip("\n")
            _log(line)
            stdout_lines.append(line)

    reader = threading.Thread(target=_reader, daemon=True)
    reader.start()

    timed_out = False
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    reader.join(timeout=10)
    _state.current_proc = None

    if timed_out:
        return TIMEOUT_EXIT_CODE, ""

    result_text = ""
    for line in stdout_lines:
        try:
            obj = json.loads(line)
            if obj.get("type") == "result":
                result_text = obj.get("result", "")
        except json.JSONDecodeError:
            pass

    return proc.returncode, result_text


# ── Main ───────────────────────────────────────────────────────────────────────


def _setup_env() -> None:
    os.environ["PATH"] = (
        f"{Path.home() / '.local' / 'bin'}:/usr/local/bin:/usr/bin:/bin"
    )
    for var, val in {
        "GIT_AUTHOR_NAME": "claude-agent",
        "GIT_AUTHOR_EMAIL": "claude-agent@localhost",
        "GIT_COMMITTER_NAME": "claude-agent",
        "GIT_COMMITTER_EMAIL": "claude-agent@localhost",
    }.items():
        os.environ.setdefault(var, val)


def _pick_project() -> tuple[int, Path]:
    """Return (run_count, project) using sequential rotation counter."""
    count = int(COUNTER_FILE.read_text().strip()) if COUNTER_FILE.exists() else 0
    idx = count % len(PROJECTS)
    COUNTER_FILE.write_text(str(count + 1))
    return count, PROJECTS[idx]


def _orchestrate(project: Path) -> tuple[str, str | None]:
    """Run the pick→orchestrate sequence; return (outcome, ticket_id)."""
    ticket_id: str | None = None

    # Housekeeping (conditional)
    if housekeeping_needed(project):
        _log(f"=== housekeeping: running {_now_iso()} ===")
        hk_rc, _ = run_skill(
            "/housekeeping",
            budget=BUDGET_HOUSEKEEPING,
            timeout_s=HOUSEKEEPING_TIMEOUT_S,
            cwd=project,
        )
        suffix = "timeout" if hk_rc == TIMEOUT_EXIT_CODE else f"rc={hk_rc}"
        _log(f"=== housekeeping: {suffix if hk_rc != 0 else 'done'} {_now_iso()} ===")
    else:
        _log(
            f"=== housekeeping: skipped "
            f"(ran within {HOUSEKEEPING_INTERVAL_S // 3600}h) {_now_iso()} ==="
        )

    # Pick ticket
    _log(f"=== pick-ticket: running {_now_iso()} ===")
    pt_rc, pt_result = run_skill(
        "/pick-ticket",
        budget=BUDGET_PICK_TICKET,
        timeout_s=PICK_TICKET_TIMEOUT_S,
        cwd=project,
    )

    if pt_rc == TIMEOUT_EXIT_CODE:
        return "aborted", None
    if pt_rc != 0:
        return "failed", None

    ticket_id = parse_pick(pt_result)
    if ticket_id is None:
        last_result_line = (
            pt_result.strip().splitlines()[-1] if pt_result.strip() else ""
        )
        _log(
            f"=== pick-ticket: idle — {last_result_line or 'IDLE: no eligible tickets'} ==="
        )
        return "idle", None

    _log(f"=== pick-ticket: picked {ticket_id} {_now_iso()} ===")

    # Orchestrate
    _log(f"=== orchestrator: running ticket {ticket_id} {_now_iso()} ===")
    oc_rc, _ = run_skill(
        f"/orchestrator {ticket_id}",
        budget=BUDGET_ORCHESTRATOR,
        timeout_s=ORCHESTRATOR_TIMEOUT_S,
        cwd=project,
    )

    if oc_rc == TIMEOUT_EXIT_CODE:
        outcome = "aborted"
    elif oc_rc != 0:
        outcome = "failed"
    else:
        # v1 simplification: rc=0 → "done"; orchestrator may write finer-grained
        # outcomes into beat-log itself, but we don't parse those here.
        outcome = "done"

    _log(f"=== orchestrator: outcome={outcome} {_now_iso()} ===")
    return outcome, ticket_id


def main() -> None:
    _state.beat_start = time.monotonic()
    signal.signal(signal.SIGTERM, _on_sigterm)
    _setup_env()

    # Lock: skip if another run is active
    LOCKFILE.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = LOCKFILE.open("w")  # held open until process exits
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(
            f"{_now_iso()}: another beat run still running, skipping.", file=sys.stderr
        )
        sys.exit(0)

    # Per-run logfile
    LOGDIR.mkdir(parents=True, exist_ok=True)
    logfile = LOGDIR / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"
    _state.log_fh = logfile.open("a")

    # Rotate old logs
    for old in sorted(LOGDIR.glob("*.log"))[:-LOG_RETAIN_COUNT]:
        old.unlink(missing_ok=True)

    # Project rotation
    count, project = _pick_project()
    _state.project = project

    _log(f"=== beat start {_now_iso()} ===")
    _log(f"Run {count}  →  project slot {count % len(PROJECTS)}: {project}")

    if not (project / ".git").is_dir():
        _log(f"ERROR: {project} is not a git repository. Aborting.")
        sys.exit(1)

    (project / ".claude" / "sweep-state").mkdir(parents=True, exist_ok=True)

    # Crash / SIGKILL recovery
    last = read_last_beat_record(project)
    if last and last.get("outcome") == "in_progress":
        try:
            last_at = last.get("last_run_at", "1970-01-01T00:00:00Z")
            last_epoch = datetime.fromisoformat(
                last_at.replace("Z", "+00:00")
            ).timestamp()
            if (time.time() - last_epoch) < CRASH_RECOVERY_WINDOW_S:
                append_beat_log(
                    project,
                    {
                        "last_run_at": _now_iso(),
                        "ticket_id": None,
                        "branch": None,
                        "PR": None,
                        "outcome": "aborted",
                        "diagnostics": "crash/SIGKILL recovery — previous run never completed spin-down",
                    },
                )
                _log(f"=== beat aborted: crash recovery {_now_iso()} ===")
                sys.exit(0)
        except (ValueError, TypeError):
            pass

    # Spin-in
    append_beat_log(project, {"outcome": "in_progress", "last_run_at": _now_iso()})

    # Orchestration
    outcome = "idle"
    ticket_id: str | None = None
    try:
        outcome, ticket_id = _orchestrate(project)
    except KeyboardInterrupt:
        outcome = "aborted"

    # Spin-down
    elapsed = int(time.monotonic() - _state.beat_start)
    finalize_beat_log(
        project,
        {
            "last_run_at": _now_iso(),
            "ticket_id": ticket_id,
            "branch": None,
            "PR": None,
            "outcome": outcome,
            "duration_s": elapsed,
        },
    )

    if not DRY_RUN:
        jq_last = subprocess.run(  # noqa: S603
            ["jq", "-cs", "last"],
            input=_beat_log_path(project).read_text(),
            capture_output=True,
            text=True,
            check=False,
        )
        _log(jq_last.stdout.strip())

    _log(f"=== beat done elapsed={elapsed}s {_now_iso()} ===")
    if _state.log_fh is not None:
        _state.log_fh.close()


if __name__ == "__main__":
    main()
