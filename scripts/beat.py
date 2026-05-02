#!/usr/bin/env python3
"""beat.py — autonomous project maintenance loop.

Replaces beat.sh + skills/beat/SKILL.md.
Control flow: [housekeeping] → pick-ticket → [raid]

Environment:
  BEAT_DRY_RUN=1   Print intended sequence without invoking Claude.
"""

import fcntl
import json
import os
import re
import secrets
import shutil
import signal
import socket
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

LOGDIR = HARNESS_DIR / "logs" / "nightbeat"
COUNTER_FILE = LOGDIR / ".run-counter"

_runtime_dir = os.environ.get("RUNTIME_DIRECTORY") or os.environ.get("XDG_RUNTIME_DIR")
_LOCK_DIR = Path(_runtime_dir) if _runtime_dir else Path.home() / ".cache"


def _lockfile(project: Path) -> Path:
    """Per-project lock so concurrent beats on different projects are allowed."""
    return _LOCK_DIR / f"nightbeat-{project.name}.lock"


HOUSEKEEPING_INTERVAL_S: int = 12 * 3600
HOUSEKEEPING_SAFETY_FLOOR_S: int = 24 * 3600
HOUSEKEEPING_TIMEOUT_S: int = 10 * 60
PICK_TICKET_TIMEOUT_S: int = 8 * 60
RAID_TIMEOUT_S: int = 30 * 60
CRASH_RECOVERY_WINDOW_S: int = 55 * 60
LOG_RETAIN_COUNT: int = 60
TIMEOUT_EXIT_CODE: int = 124  # matches bash `timeout` convention

BUDGET_HOUSEKEEPING: float = 0.75
BUDGET_PICK_TICKET: float = 0.75
BUDGET_RAID: float = 5.00

MODEL_SONNET: str = "sonnet"
MODEL_HAIKU: str = "claude-haiku-4-5-20251001"

PROJECTS_CONFIG: Path = HARNESS_DIR / "scripts" / "projects.json"

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


# ── Per-project configuration ─────────────────────────────────────────────────


@dataclass
class ProjectConfig:
    """Per-project beat settings; budget fields default to the global constants."""

    path: Path
    budget_housekeeping: float = BUDGET_HOUSEKEEPING
    budget_pick_ticket: float = BUDGET_PICK_TICKET
    pick_ticket_model: str = MODEL_HAIKU  # model used when repo has no recent commits


_BUILTIN_PROJECTS: list[ProjectConfig] = [
    ProjectConfig(
        path=Path.home() / "aedist-technical-report",
        budget_housekeeping=0.40,
        budget_pick_ticket=0.50,
    ),
    ProjectConfig(
        path=Path.home() / "cadens",
        budget_housekeeping=0.40,
        budget_pick_ticket=0.50,
    ),
    ProjectConfig(path=Path.home() / "Climate_finance"),
    ProjectConfig(path=Path.home() / "fuzzy-corpus"),
    ProjectConfig(
        path=HARNESS_DIR,
        budget_housekeeping=0.40,
        budget_pick_ticket=0.50,
    ),
]

_PROJ_KEYS = {"budget_housekeeping", "budget_pick_ticket", "pick_ticket_model"}


def load_projects(config_path: Path) -> list[ProjectConfig]:
    """Load project list from JSON; fall back to built-in defaults on any error."""
    if not config_path.exists():
        print(
            f"[beat] {config_path} not found, using built-in defaults", file=sys.stderr
        )
        return list(_BUILTIN_PROJECTS)
    try:
        entries = json.loads(config_path.read_text())
        return [
            ProjectConfig(
                path=Path(e["path"]).expanduser(),
                **{k: e[k] for k in _PROJ_KEYS if k in e},
            )
            for e in entries
        ]
    except Exception as exc:  # noqa: BLE001
        print(
            f"[beat] error loading {config_path}: {exc}, using built-in defaults",
            file=sys.stderr,
        )
        return list(_BUILTIN_PROJECTS)


PROJECTS: list[ProjectConfig] = load_projects(PROJECTS_CONFIG)


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


def _cleanup_stale_in_progress(project: Path) -> None:
    """Rewrite any in_progress record older than CRASH_RECOVERY_WINDOW_S to aborted.

    Crash recovery only catches the most-recent record; this catches orphans
    buried under subsequent done/failed records when the 55-min window elapsed
    before the project was next visited.
    """
    path = _beat_log_path(project)
    if not path.exists():
        return
    cutoff = time.time() - CRASH_RECOVERY_WINDOW_S
    lines = path.read_text().splitlines()
    changed = False
    new_lines: list[str] = []
    for line in lines:
        if line.strip():
            try:
                rec = json.loads(line)
                if rec.get("outcome") == "in_progress":
                    epoch = datetime.fromisoformat(
                        rec.get("last_run_at", "1970-01-01T00:00:00Z").replace(
                            "Z", "+00:00"
                        )
                    ).timestamp()
                    if epoch < cutoff:
                        rec["outcome"] = "aborted"
                        rec["diagnostics"] = (
                            "stale in_progress — cleaned on next beat start"
                        )
                        line = json.dumps(rec, separators=(",", ":"))
                        changed = True
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        new_lines.append(line)
    if changed:
        path.write_text("\n".join(new_lines) + "\n")
        _log(f"=== startup: cleaned stale in_progress records in {project.name} ===")


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
    """Return True when housekeeping should run.

    Skip when the repo is idle (no commits since last housekeeping)
    but enforce a 24h safety floor.
    """
    result = subprocess.run(  # noqa: S603
        ["git", "log", "--grep=housekeeping", "-1", "--format=%ct %H"],
        capture_output=True,
        text=True,
        check=False,
        cwd=project,
    )
    raw = result.stdout.strip()
    if not raw:
        return True
    parts = raw.split(maxsplit=1)
    if len(parts) < 2:
        return True
    try:
        age = time.time() - int(parts[0])
    except ValueError:
        return True
    if age <= HOUSEKEEPING_INTERVAL_S:
        return False
    if age > HOUSEKEEPING_SAFETY_FLOOR_S:
        last_hk_dt = datetime.fromtimestamp(int(parts[0]), tz=timezone.utc)
        if _repo_frozen_since(project, last_hk_dt):
            return False
        return True
    # Between interval and safety floor: run only if repo has activity.
    activity = subprocess.run(  # noqa: S603
        ["git", "rev-list", "--count", f"{parts[1]}..HEAD"],
        capture_output=True,
        text=True,
        check=False,
        cwd=project,
    )
    try:
        return int(activity.stdout.strip()) > 0
    except ValueError:
        return True


def _repo_frozen_since(project: Path, since: datetime) -> bool:
    """Return True when no commits have landed since `since`."""
    result = subprocess.run(  # noqa: S603
        ["git", "log", f"--since={since.isoformat()}", "--oneline"],
        capture_output=True,
        text=True,
        check=False,
        cwd=project,
    )
    return not result.stdout.strip()


def _repo_active(project: Path) -> bool:
    """Return True when at least one commit landed in the last 24 hours."""
    result = subprocess.run(  # noqa: S603
        ["git", "log", "--since=24h", "--oneline"],
        capture_output=True,
        text=True,
        check=False,
        cwd=project,
    )
    return bool(result.stdout.strip())


# ── Pick-ticket output parser ─────────────────────────────────────────────────


def parse_pick(result_text: str) -> str | None:
    """Return 4-digit ticket ID from PICK: line, or None for IDLE / no match."""
    if re.search(r"\bIDLE\b", result_text, re.IGNORECASE):
        return None
    m = re.search(r"\bPICK:\s*(\d{4})\b", result_text)
    return m.group(1) if m else None


# ── Claude subprocess ──────────────────────────────────────────────────────────


def _claude_argv(
    skill: str,
    budget: float,
    *,
    project_scoped: bool = False,
    model: str = MODEL_SONNET,
) -> list[str]:
    argv = [
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
        model,
        "--settings",
        str(HARNESS_DIR / "scripts" / "beat-settings.json"),
    ]
    if not project_scoped:
        # Harness context for skills that need workflow awareness (housekeeping).
        # Omitted for pick-ticket / raid to prevent cross-project ticket leakage.
        argv += ["--add-dir", str(HARNESS_DIR)]
    argv += ["--add-dir", ".", "-p", skill]
    return argv


def run_skill(
    skill: str,
    *,
    budget: float,
    timeout_s: int,
    cwd: Path,
    project_scoped: bool = False,
    model: str = MODEL_SONNET,
) -> tuple[int, str]:
    """Invoke a Claude skill; return (exit_code, last_result_text).

    Streams stdout line-by-line for live logging.
    Returns exit_code=TIMEOUT_EXIT_CODE on timeout.
    project_scoped=True omits --add-dir harness to prevent cross-project ticket leakage.
    """
    argv = _claude_argv(skill, budget, project_scoped=project_scoped, model=model)

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


def _pick_project() -> tuple[int, ProjectConfig]:
    """Return (run_count, project_config).

    If BEAT_PROJECT is set, use that path directly (counter still advances).
    If the path matches a known project, return its config; otherwise build a
    default-budget ProjectConfig for the override path.
    Otherwise use sequential rotation across PROJECTS.
    """
    count = int(COUNTER_FILE.read_text().strip()) if COUNTER_FILE.exists() else 0
    COUNTER_FILE.write_text(str(count + 1))
    override = os.environ.get("BEAT_PROJECT")
    if override:
        override_path = Path(override).resolve()
        for cfg in PROJECTS:
            if cfg.path == override_path:
                return count, cfg
        return count, ProjectConfig(path=override_path)
    idx = count % len(PROJECTS)
    return count, PROJECTS[idx]


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        ["git", *args], capture_output=True, text=True, check=False, cwd=cwd
    )


def _gh_available() -> bool:
    return shutil.which("gh") is not None


PR_CHECK_POLL_INTERVAL_S: int = 15
PR_CHECK_TIMEOUT_S: int = 10 * 60
PR_CHECK_TRANSIENT_RETRIES: int = 3


def _wait_for_pr_checks(branch: str, *, cwd: Path) -> bool:
    """Block until all PR checks settle. Return True iff all pass.

    Tolerates a small number of transient `gh pr checks` failures
    (rate limit, network blip) before giving up.
    """
    deadline = time.monotonic() + PR_CHECK_TIMEOUT_S
    transient_failures = 0
    while time.monotonic() < deadline:
        result = subprocess.run(  # noqa: S603, S607
            ["gh", "pr", "checks", branch, "--json", "name,bucket"],
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
        if result.returncode != 0:
            transient_failures += 1
            if transient_failures > PR_CHECK_TRANSIENT_RETRIES:
                return False
            time.sleep(PR_CHECK_POLL_INTERVAL_S)
            continue
        try:
            checks = json.loads(result.stdout)
        except json.JSONDecodeError:
            transient_failures += 1
            if transient_failures > PR_CHECK_TRANSIENT_RETRIES:
                return False
            time.sleep(PR_CHECK_POLL_INTERVAL_S)
            continue
        transient_failures = 0
        if not checks:
            time.sleep(PR_CHECK_POLL_INTERVAL_S)
            continue
        buckets = {c.get("bucket") for c in checks}
        if "pending" in buckets:
            time.sleep(PR_CHECK_POLL_INTERVAL_S)
            continue
        return buckets <= {"pass"}
    return False


def _housekeeping_phase(project: ProjectConfig) -> str:
    """Run housekeeping on a dedicated branch; PR+merge if commits land.

    Returns one of:
      "skipped"    — housekeeping_needed was False
      "no-changes" — skill ran clean, produced no commits
      "merged"     — PR opened, CI green, squash-merged into main
      "deferred"   — commits exist locally; PR/merge automation off (no gh
                     or BEAT_HOUSEKEEPING_PR != 1) — branch left for human
      "ci-failed"  — PR opened but at least one check failed
      "timeout"    — skill timed out
      "failed"     — git/gh/skill error
    """
    path = project.path
    if not housekeeping_needed(path):
        _log(f"=== housekeeping: skipped {_now_iso()} ===")
        return "skipped"

    base = _git("rev-parse", "origin/main", cwd=path).stdout.strip()
    if not base:
        _log("=== housekeeping: cannot resolve origin/main ===")
        return "failed"

    nonce = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + secrets.token_hex(2)
    )
    branch = f"claude/housekeeping-{nonce}"
    if _git("checkout", "-B", branch, base, cwd=path).returncode != 0:
        _log(f"=== housekeeping: failed to create {branch} ===")
        return "failed"

    _log(f"=== housekeeping: running on {branch} {_now_iso()} ===")
    os.environ["BEAT_HOUSEKEEPING_BRANCH"] = branch
    try:
        hk_rc, _ = run_skill(
            "/housekeeping",
            budget=project.budget_housekeeping,
            timeout_s=HOUSEKEEPING_TIMEOUT_S,
            cwd=path,
        )
    finally:
        os.environ.pop("BEAT_HOUSEKEEPING_BRANCH", None)

    if hk_rc == TIMEOUT_EXIT_CODE:
        _log(f"=== housekeeping: timeout — {branch} left in place {_now_iso()} ===")
        return "timeout"
    if hk_rc != 0:
        _log(f"=== housekeeping: rc={hk_rc} on {branch} {_now_iso()} ===")
        return "failed"

    n = _git("rev-list", "--count", f"{base}..HEAD", cwd=path).stdout.strip() or "0"
    if int(n) == 0:
        _log("=== housekeeping: no commits, deleting branch ===")
        _git("checkout", "main", cwd=path)
        _git("branch", "-D", branch, cwd=path)
        return "no-changes"

    _log(f"=== housekeeping: {n} commit(s) on {branch} ===")

    if not (os.environ.get("BEAT_HOUSEKEEPING_PR") == "1" and _gh_available()):
        # Switch back to main so pick-ticket → raid don't run on the
        # housekeeping branch and pick up its commits as their base.
        _git("checkout", "main", cwd=path)
        _log(f"=== housekeeping: deferred — branch {branch} ready for review ===")
        return "deferred"

    if _git("push", "-u", "origin", branch, cwd=path).returncode != 0:
        return "failed"
    log_lines = _git(
        "log", "--format=- %s", f"{base}..HEAD", cwd=path
    ).stdout.strip()
    body = (
        "Automated nightbeat housekeeping sweep.\n\n## Changes\n\n"
        + (log_lines or "(none)")
    )
    pr = subprocess.run(  # noqa: S603, S607
        [
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            branch,
            "--title",
            f"chore: housekeeping fixes (sweep) — {n} commit(s)",
            "--body",
            body,
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=path,
    )
    if pr.returncode != 0:
        _log(f"=== housekeeping: gh pr create failed: {pr.stderr.strip()} ===")
        return "failed"

    if not _wait_for_pr_checks(branch, cwd=path):
        _log(f"=== housekeeping: CI red on {branch} — aborting beat ===")
        return "ci-failed"

    merge = subprocess.run(  # noqa: S603, S607
        ["gh", "pr", "merge", branch, "--squash", "--delete-branch"],
        capture_output=True,
        text=True,
        check=False,
        cwd=path,
    )
    if merge.returncode != 0:
        _log(f"=== housekeeping: gh pr merge failed: {merge.stderr.strip()} ===")
        return "failed"

    _git("checkout", "main", cwd=path)
    _git("pull", "--ff-only", "origin", "main", cwd=path)
    _log(f"=== housekeeping: merged {branch} {_now_iso()} ===")
    return "merged"


def _raid(project: ProjectConfig) -> tuple[str, str | None]:
    """Run the pick→raid sequence; return (outcome, ticket_id)."""
    ticket_id: str | None = None
    path = project.path

    # Housekeeping (conditional). Aborts beat on failure/timeout/CI-red so
    # pick-ticket → raid never runs against a known-bad main.
    hk_outcome = _housekeeping_phase(project)
    if hk_outcome in ("failed", "timeout", "ci-failed"):
        return "aborted", None

    # Pick ticket
    hostname = socket.gethostname()
    pick_model = MODEL_SONNET if _repo_active(path) else project.pick_ticket_model
    _log(f"=== pick-ticket: running model={pick_model} {_now_iso()} ===")
    pt_rc, pt_result = run_skill(
        f"/pick-ticket\n\nRunning on: {hostname}",
        budget=project.budget_pick_ticket,
        timeout_s=PICK_TICKET_TIMEOUT_S,
        cwd=path,
        project_scoped=True,
        model=pick_model,
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

    # Raid
    _log(f"=== raid: running ticket {ticket_id} {_now_iso()} ===")
    oc_rc, _ = run_skill(
        f"/raid {ticket_id}\n\nRunning on: {hostname}",
        budget=BUDGET_RAID,
        timeout_s=RAID_TIMEOUT_S,
        cwd=path,
        project_scoped=True,
    )

    if oc_rc == TIMEOUT_EXIT_CODE:
        outcome = "aborted"
    elif oc_rc != 0:
        outcome = "failed"
    else:
        # v1 simplification: rc=0 → "done"; raid may write finer-grained
        # outcomes into beat-log itself, but we don't parse those here.
        outcome = "done"
        # Warn if raid exited cleanly but left the ticket open (double-pick risk).
        ticket_files = list(path.glob(f"tickets/{ticket_id}-*.erg"))
        if ticket_files:
            status = next(
                (
                    ln.split()[1]
                    for ln in ticket_files[0].read_text().splitlines()
                    if ln.startswith("Status:")
                ),
                "",
            )
            if status and status != "closed":
                _log(
                    f"=== warning: raid done but ticket {ticket_id}"
                    f" Status: {status} (not closed) — double-pick risk ==="
                )

    _log(f"=== raid: outcome={outcome} {_now_iso()} ===")
    return outcome, ticket_id


def main() -> None:
    _state.beat_start = time.monotonic()
    signal.signal(signal.SIGTERM, _on_sigterm)
    _setup_env()

    # Per-run logfile (opened before lock so startup messages are captured)
    LOGDIR.mkdir(parents=True, exist_ok=True)
    logfile = LOGDIR / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"
    _state.log_fh = logfile.open("a")

    # Rotate old logs
    for old in sorted(LOGDIR.glob("*.log"))[:-LOG_RETAIN_COUNT]:
        old.unlink(missing_ok=True)

    # Project rotation
    count, project = _pick_project()
    path = project.path
    _state.project = path

    # Per-project lock: allows concurrent beats on different projects
    _LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_fh = _lockfile(path).open("w")  # held open until process exits
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        _log(f"beat already running for {path.name}, skipping.")
        lock_fh.close()
        sys.exit(0)

    _log(f"=== beat start {_now_iso()} ===")
    _log(f"Run {count}  →  project slot {count % len(PROJECTS)}: {path}")

    if not (path / ".git").is_dir():
        _log(f"ERROR: {path} is not a git repository. Aborting.")
        sys.exit(1)

    (path / ".claude" / "sweep-state").mkdir(parents=True, exist_ok=True)

    # Layer-1 cleanup: rewrite buried stale in_progress records that crash
    # recovery missed (it only checks the most-recent record within 55 min).
    _cleanup_stale_in_progress(path)

    # Crash / SIGKILL recovery
    last = read_last_beat_record(path)
    if last and last.get("outcome") == "in_progress":
        try:
            last_at = last.get("last_run_at", "1970-01-01T00:00:00Z")
            last_epoch = datetime.fromisoformat(
                last_at.replace("Z", "+00:00")
            ).timestamp()
            if (time.time() - last_epoch) < CRASH_RECOVERY_WINDOW_S:
                append_beat_log(
                    path,
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
    append_beat_log(path, {"outcome": "in_progress", "last_run_at": _now_iso()})

    # Orchestration
    outcome = "idle"
    ticket_id: str | None = None
    try:
        outcome, ticket_id = _raid(project)
    except KeyboardInterrupt:
        outcome = "aborted"

    # Spin-down
    elapsed = int(time.monotonic() - _state.beat_start)
    finalize_beat_log(
        path,
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
            input=_beat_log_path(path).read_text(),
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
