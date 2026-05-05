#!/usr/bin/env python3
"""nightbeat-report.py — morning review of autonomous nightbeat runs.

Parses ~/.claude/logs/nightbeat/*.log files and per-project beat-log.jsonl.
Usage:
  nightbeat-report.py                  # since last 22:00 local time
  nightbeat-report.py --hours 12       # last 12 hours
  nightbeat-report.py --since 2026-04-25T22:00:00Z
  nightbeat-report.py --full           # show full raid result text
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

HARNESS_DIR = Path.home() / ".claude"
LOGDIR = HARNESS_DIR / "logs" / "nightbeat"
PERMISSION_DIFFS_DIR = HARNESS_DIR / "telemetry" / "permission-diffs"
PROJECTS_CONFIG = HARNESS_DIR / "scripts" / "projects.json"


def _load_rotation_projects() -> list[Path]:
    """Load project paths from projects.json (same source as beat.py)."""
    if not PROJECTS_CONFIG.exists():
        return []
    try:
        entries = json.loads(PROJECTS_CONFIG.read_text())
        return [Path(e["path"]).expanduser() for e in entries]
    except Exception:
        return []


_MARKER = re.compile(r"^=== (.+?) (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) ===$")
_RUN_RE = re.compile(r"^Run \d+\s+\S+\s+project slot \d+: (.+)$")
_LOCK_RE = re.compile(r"beat already running for (\S+), skipping")


@dataclass
class SkillResult:
    cost_usd: float = 0.0
    num_turns: int = 0
    result_text: str = ""
    is_error: bool = False
    subtype: str = ""
    permission_denials: list[str] = field(default_factory=list)


@dataclass
class BeatRun:
    logfile: Path
    start_utc: datetime
    project: Path | None = None
    skipped_lock: str = ""  # non-empty = lock-contention skip (project name)

    hk_status: str = ""  # skipped / running / done / rc=N / timeout
    hk_result: SkillResult | None = None

    pick_status: str = ""  # idle / picked / timeout / failed
    ticket_id: str | None = None
    pick_result: SkillResult | None = None

    oc_status: str = ""  # done / failed / aborted
    oc_result: SkillResult | None = None

    elapsed_s: int | None = None


# ── Parsing ────────────────────────────────────────────────────────────────────


def _try_result_json(line: str) -> SkillResult | None:
    if not line.startswith("{"):
        return None
    try:
        obj = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(obj, dict) or obj.get("type") != "result":
        return None
    denials = [d.get("tool_name", "?") for d in obj.get("permission_denials", [])]
    return SkillResult(
        cost_usd=obj.get("total_cost_usd") or 0.0,
        num_turns=obj.get("num_turns", 0),
        result_text=obj.get("result", ""),
        is_error=bool(obj.get("is_error")),
        subtype=obj.get("subtype", ""),
        permission_denials=denials,
    )


def parse_log(path: Path) -> BeatRun:
    stem = path.stem
    try:
        start_utc = datetime.strptime(stem, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        start_utc = datetime.now(timezone.utc)

    run = BeatRun(logfile=path, start_utc=start_utc)
    section: str | None = None  # "hk" | "pick" | "oc"

    try:
        text = path.read_text(errors="replace")
    except OSError:
        return run

    for line in text.splitlines():
        # Lock-contention skip (no further content)
        m = _LOCK_RE.search(line)
        if m:
            run.skipped_lock = m.group(1)
            return run

        # Project path line
        m = _RUN_RE.search(line)
        if m:
            run.project = Path(m.group(1).strip())
            continue

        # Marker lines
        m = _MARKER.search(line)
        if m:
            label = m.group(1)
            _handle_marker(label, line, run, section_ref := [section])
            section = section_ref[0]
            continue

        # "beat done elapsed=Ns timestamp" (no trailing ===)
        dm = re.search(r"=== beat done elapsed=(\d+)s", line)
        if dm:
            run.elapsed_s = int(dm.group(1))
            continue

        # Result JSON
        result = _try_result_json(line)
        if result is not None:
            if section == "hk":
                run.hk_result = result
            elif section == "pick":
                run.pick_result = result
            elif section == "oc":
                run.oc_result = result

    return run


def _handle_marker(label: str, line: str, run: BeatRun, section_ref: list) -> None:
    """Mutate run and section_ref[0] in-place based on a === ... === marker."""
    if "beat start" in label:
        pass

    elif label.startswith("housekeeping:"):
        status = label.removeprefix("housekeeping:").strip()
        if "running" in status:
            run.hk_status = "running"
            section_ref[0] = "hk"
        elif "skipped" in status:
            run.hk_status = "skipped"
            section_ref[0] = None
        elif "timeout" in status:
            run.hk_status = "timeout"
            section_ref[0] = None
        elif status == "done" or status.startswith("done "):
            run.hk_status = "done"
            section_ref[0] = None
        else:
            run.hk_status = status.split()[0]  # e.g. "rc=1"
            section_ref[0] = None

    elif label.startswith("pick-ticket:"):
        status = label.removeprefix("pick-ticket:").strip()
        if "running" in status:
            section_ref[0] = "pick"
        elif "idle" in status:
            run.pick_status = "idle"
            section_ref[0] = None
        elif "timeout" in status:
            run.pick_status = "timeout"
            section_ref[0] = None
        else:
            m = re.search(r"picked (\d{4})", status)
            if m:
                run.ticket_id = m.group(1)
                run.pick_status = "picked"
            section_ref[0] = None

    elif label.startswith(("raid:", "orchestrator:")):
        # Dual-accept for one quarter post-rename (ticket 0045).
        # TODO: drop the "orchestrator:" prefix after 2026-07-28.
        prefix = "raid:" if label.startswith("raid:") else "orchestrator:"
        status = label.removeprefix(prefix).strip()
        if "running ticket" in status:
            section_ref[0] = "oc"
        else:
            m = re.search(r"outcome=(\w+)", status)
            if m:
                run.oc_status = m.group(1)
            section_ref[0] = None

    elif "beat aborted" in label or "beat SIGTERM" in label:
        run.oc_status = "aborted"
        section_ref[0] = None

    elif "beat done" in label:
        m = re.search(r"elapsed=(\d+)s", line)
        if m:
            run.elapsed_s = int(m.group(1))
        section_ref[0] = None


# ── Formatting ─────────────────────────────────────────────────────────────────


def _fmt_dur(s: int | None) -> str:
    if s is None:
        return "—"
    m, sec = divmod(s, 60)
    return f"{m}m{sec:02d}s"


def _run_cost(run: BeatRun) -> float:
    return sum(
        r.cost_usd
        for r in (run.hk_result, run.pick_result, run.oc_result)
        if r is not None
    )


def _outcome(run: BeatRun) -> str:
    if run.skipped_lock:
        return "locked"
    if run.oc_status:
        return run.oc_status
    if run.pick_status:
        return run.pick_status
    return run.hk_status or "?"


def _notes(run: BeatRun) -> str:
    parts = []
    if run.hk_status and run.hk_status not in ("skipped", "done", "running", ""):
        parts.append(f"hk:{run.hk_status}")
    for r in (run.hk_result, run.pick_result, run.oc_result):
        if r and r.is_error and r.subtype:
            parts.append(r.subtype)
        if r:
            for d in r.permission_denials:
                parts.append(f"denied:{d}")
    return "; ".join(dict.fromkeys(parts))  # deduplicate, preserve order


# ── Beat-log summary ───────────────────────────────────────────────────────────


def _beat_log_night_summary(proj: Path, since: datetime) -> dict:
    path = proj / "beat-log.jsonl"
    counts: dict[str, int] = {}
    last: dict = {}
    if not path.exists():
        return {"counts": counts, "last": last}
    since_str = since.strftime("%Y-%m-%dT")
    for raw in path.read_text().splitlines():
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        last = rec
        if rec.get("last_run_at", "") >= since_str:
            outcome = rec.get("outcome", "?")
            if outcome != "in_progress":  # orphans cleaned by beat.py; skip noise
                counts[outcome] = counts.get(outcome, 0) + 1
    return {"counts": counts, "last": last}


# ── Unreviewed permission diffs (ticket 0043) ─────────────────────────────────


def _unreviewed_permission_diffs(since: datetime) -> list[tuple[Path, int]]:
    """Return permission-diff files modified since the report window start.

    These are weekly proposals from /fewer-permission-prompts that have not
    been reviewed (we treat any file under the dir touched in the window as
    unreviewed — review = move/delete the file).
    """
    if not PERMISSION_DIFFS_DIR.is_dir():
        return []
    cutoff = since.timestamp()
    out: list[tuple[Path, int]] = []
    for p in sorted(PERMISSION_DIFFS_DIR.glob("*.diff")):
        try:
            if p.stat().st_mtime < cutoff:
                continue
            line_count = sum(1 for _ in p.open())
        except OSError:
            continue
        out.append((p, line_count))
    return out


# ── Default since ──────────────────────────────────────────────────────────────


def _default_since() -> datetime:
    local_now = datetime.now().astimezone()
    today_22 = local_now.replace(hour=22, minute=0, second=0, microsecond=0)
    since_local = today_22 if local_now >= today_22 else today_22 - timedelta(days=1)
    return since_local.astimezone(timezone.utc).replace(tzinfo=timezone.utc)


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Morning nightbeat review")
    parser.add_argument("--since", help="ISO timestamp, e.g. 2026-04-25T22:00:00Z")
    parser.add_argument("--hours", type=int, help="Last N hours")
    parser.add_argument(
        "--full", action="store_true", help="Show full raid result text"
    )
    args = parser.parse_args()

    if args.hours is not None:
        since = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    elif args.since:
        since = datetime.fromisoformat(args.since.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    else:
        since = _default_since()

    # Collect and filter log files
    all_logs = sorted(LOGDIR.glob("*.log"))
    in_window: list[Path] = []
    for p in all_logs:
        try:
            ts = datetime.strptime(p.stem, "%Y%m%dT%H%M%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        if ts >= since:
            in_window.append(p)

    if not in_window:
        since_local = since.astimezone().strftime("%Y-%m-%d %H:%M %Z")
        print(f"No nightbeat runs found since {since_local}")
        sys.exit(0)

    runs = [parse_log(p) for p in in_window]

    # ── Header ──────────────────────────────────────────────────────────────────
    since_local = since.astimezone().strftime("%Y-%m-%d %H:%M %Z")
    print(f"\nNight Beat Report — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Runs since {since_local}  ({len(runs)} runs in window)\n")

    # ── Run table ───────────────────────────────────────────────────────────────
    COL = "  "
    hdr = f"{'#':>3}{COL}{'UTC':>9}{COL}{'Project':<24}{COL}{'Ticket':>6}{COL}{'Outcome':<8}{COL}{'Elapsed':>8}{COL}{'Cost':>7}{COL}Notes"
    print(hdr)
    print("─" * len(hdr))
    for i, run in enumerate(runs, 1):
        proj = (
            run.project.name
            if run.project
            else (f"(locked:{run.skipped_lock})" if run.skipped_lock else "?")
        )
        time_s = run.start_utc.strftime("%H:%M %a")
        ticket = run.ticket_id or "—"
        outcome = _outcome(run)
        elapsed = _fmt_dur(run.elapsed_s)
        cost = f"${_run_cost(run):.2f}"
        notes = _notes(run)
        print(
            f"{i:>3}{COL}{time_s:>9}{COL}{proj:<24}{COL}{ticket:>6}{COL}{outcome:<8}{COL}{elapsed:>8}{COL}{cost:>7}{COL}{notes}"
        )

    # ── Raid results ────────────────────────────────────────────────────────────
    oc_runs = [r for r in runs if r.oc_result and r.oc_result.result_text]
    if oc_runs:
        print(f"\n{'═' * 72}")
        print("RAID RESULTS")
        print(f"{'═' * 72}")
        TRUNC = 1200
        for run in oc_runs:
            proj = run.project.name if run.project else "?"
            time_s = run.start_utc.strftime("%H:%M UTC")
            ticket = run.ticket_id or "?"
            cost_s = f"${run.oc_result.cost_usd:.2f}" if run.oc_result else ""
            turns = f"{run.oc_result.num_turns}t" if run.oc_result else ""
            print(
                f"\n[{time_s}] {proj} / ticket {ticket} — {run.oc_status or '?'}  {turns}  {cost_s}"
            )
            print("─" * 60)
            text = run.oc_result.result_text
            if not args.full and len(text) > TRUNC:
                text = (
                    text[:TRUNC]
                    + f"\n  […{len(run.oc_result.result_text) - TRUNC} chars truncated — use --full]"
                )
            for ln in text.splitlines():
                print(f"  {ln}")

    # ── Issues ──────────────────────────────────────────────────────────────────
    issues: list[str] = []
    for run in runs:
        proj = run.project.name if run.project else "?"
        ts = run.start_utc.strftime("%H:%M")
        if "rc=" in run.hk_status:
            issues.append(f"[{ts}] {proj}: housekeeping {run.hk_status}")
        if run.hk_status == "timeout":
            issues.append(f"[{ts}] {proj}: housekeeping TIMEOUT")
        if run.oc_status in ("failed", "aborted"):
            issues.append(f"[{ts}] {proj}/{run.ticket_id or '—'}: raid {run.oc_status}")
        if run.pick_status == "timeout":
            issues.append(f"[{ts}] {proj}: pick-ticket TIMEOUT")
        for r in (run.hk_result, run.pick_result, run.oc_result):
            if r and r.is_error and r.subtype not in ("", "error_max_budget_usd"):
                issues.append(f"[{ts}] {proj}: {r.subtype}")
            if r:
                for d in r.permission_denials:
                    issues.append(f"[{ts}] {proj}: permission denied — {d}")

    if issues:
        print(f"\n{'═' * 72}")
        print("WARNINGS / ISSUES")
        print(f"{'═' * 72}")
        seen: set[str] = set()
        for issue in issues:
            if issue not in seen:
                print(f"  {issue}")
                seen.add(issue)

    # ── Unreviewed permission diffs (ticket 0043) ───────────────────────────────
    pending = _unreviewed_permission_diffs(since)
    if pending:
        print(f"\n{'═' * 72}")
        print("UNREVIEWED PERMISSION DIFFS")
        print(f"{'═' * 72}")
        for path, line_count in pending:
            print(f"  UNREVIEWED PERMISSION DIFF: {path.name} ({line_count} lines)")
        print(f"  review at: {PERMISSION_DIFFS_DIR}")

    # ── Totals ──────────────────────────────────────────────────────────────────
    n_done = sum(1 for r in runs if r.oc_status == "done")
    n_failed = sum(1 for r in runs if r.oc_status in ("failed", "aborted"))
    n_idle = sum(1 for r in runs if r.pick_status == "idle")
    n_locked = sum(1 for r in runs if r.skipped_lock)
    hk_cost = sum(r.hk_result.cost_usd for r in runs if r.hk_result)
    pick_cost = sum(r.pick_result.cost_usd for r in runs if r.pick_result)
    oc_cost = sum(r.oc_result.cost_usd for r in runs if r.oc_result)
    total = hk_cost + pick_cost + oc_cost

    print(f"\n{'═' * 72}")
    print("TOTALS")
    print(f"{'═' * 72}")
    parts = [f"runs:{len(runs)}", f"done:{n_done}", f"idle:{n_idle}"]
    if n_failed:
        parts.append(f"failed:{n_failed}")
    if n_locked:
        parts.append(f"locked:{n_locked}")
    print(f"  {' | '.join(parts)}")
    print(
        f"  cost:  hk=${hk_cost:.2f}  pick=${pick_cost:.2f}  orch=${oc_cost:.2f}  total=${total:.2f}"
    )

    # ── Per-project beat-log summary ────────────────────────────────────────────
    rotation = _load_rotation_projects()
    print(f"\n{'═' * 72}")
    print("PER-PROJECT SUMMARY  (from beat-log.jsonl)")
    print(f"{'═' * 72}")
    for proj_path in rotation:
        summary = _beat_log_night_summary(proj_path, since)
        counts = summary["counts"]
        last = summary["last"]
        if not counts and not last:
            continue
        parts_p: list[str] = []
        for outcome in ("done", "idle", "failed", "aborted"):
            if counts.get(outcome):
                parts_p.append(f"{outcome}:{counts[outcome]}")
        last_ticket = last.get("ticket_id") or "—"
        last_outcome = last.get("outcome", "?")
        last_at = (last.get("last_run_at") or "")[:16].replace("T", " ")
        counts_str = "  ".join(parts_p) if parts_p else "no runs"
        print(
            f"  {proj_path.name:<30}  {counts_str:<28}  last: {last_ticket} ({last_outcome}) @ {last_at}"
        )

    print()


if __name__ == "__main__":
    main()
