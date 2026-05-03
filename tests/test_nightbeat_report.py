"""Tests for scripts/nightbeat-report.py — log parser dual-accept window."""

import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
spec = importlib.util.spec_from_file_location(
    "nightbeat_report", SCRIPTS / "nightbeat-report.py"
)
nbr = importlib.util.module_from_spec(spec)
sys.modules["nightbeat_report"] = nbr
spec.loader.exec_module(nbr)


def _write_log(tmp_path: Path, body: str) -> Path:
    log = tmp_path / "20260429T020000Z.log"
    log.write_text(body)
    return log


def test_parser_accepts_legacy_orchestrator_label(tmp_path):
    body = (
        "BEAT_START project=/tmp/p\n"
        "=== beat start 2026-04-29T02:00:00Z ===\n"
        "=== pick-ticket: picked 0001 2026-04-29T02:01:00Z ===\n"
        "=== orchestrator: running ticket 0001 2026-04-29T02:02:00Z ===\n"
        "=== orchestrator: outcome=done 2026-04-29T02:30:00Z ===\n"
        "=== beat done elapsed=1800s 2026-04-29T02:30:00Z ===\n"
    )
    run = nbr.parse_log(_write_log(tmp_path, body))
    assert run.ticket_id == "0001"
    assert run.oc_status == "done"


def test_parser_accepts_new_raid_label(tmp_path):
    body = (
        "BEAT_START project=/tmp/p\n"
        "=== beat start 2026-04-29T02:00:00Z ===\n"
        "=== pick-ticket: picked 0042 2026-04-29T02:01:00Z ===\n"
        "=== raid: running ticket 0042 2026-04-29T02:02:00Z ===\n"
        "=== raid: outcome=failed 2026-04-29T02:30:00Z ===\n"
        "=== beat done elapsed=1700s 2026-04-29T02:30:00Z ===\n"
    )
    run = nbr.parse_log(_write_log(tmp_path, body))
    assert run.ticket_id == "0042"
    assert run.oc_status == "failed"


def test_parser_accepts_mixed_labels_in_one_log(tmp_path):
    body = (
        "BEAT_START project=/tmp/p\n"
        "=== beat start 2026-04-29T02:00:00Z ===\n"
        "=== pick-ticket: picked 0099 2026-04-29T02:01:00Z ===\n"
        "=== orchestrator: running ticket 0099 2026-04-29T02:02:00Z ===\n"
        "=== raid: outcome=aborted 2026-04-29T02:30:00Z ===\n"
    )
    run = nbr.parse_log(_write_log(tmp_path, body))
    assert run.oc_status == "aborted"


# ── Unreviewed permission diffs (ticket 0043) ─────────────────────────────────


def test_unreviewed_permission_diffs_picks_recent(tmp_path, monkeypatch):
    diffs_dir = tmp_path / "permission-diffs"
    diffs_dir.mkdir()
    fresh = diffs_dir / "2026-05-03.diff"
    fresh.write_text("line1\nline2\nline3\n")
    monkeypatch.setattr(nbr, "PERMISSION_DIFFS_DIR", diffs_dir)

    from datetime import datetime, timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(hours=1)
    found = nbr._unreviewed_permission_diffs(since)
    assert len(found) == 1
    assert found[0][0] == fresh
    assert found[0][1] == 3


def test_unreviewed_permission_diffs_ignores_old(tmp_path, monkeypatch):
    import os
    from datetime import datetime, timedelta, timezone

    diffs_dir = tmp_path / "permission-diffs"
    diffs_dir.mkdir()
    old = diffs_dir / "2026-04-01.diff"
    old.write_text("ancient\n")
    # Backdate mtime by 30 days.
    old_ts = (datetime.now() - timedelta(days=30)).timestamp()
    os.utime(old, (old_ts, old_ts))
    monkeypatch.setattr(nbr, "PERMISSION_DIFFS_DIR", diffs_dir)

    since = datetime.now(timezone.utc) - timedelta(hours=8)
    assert nbr._unreviewed_permission_diffs(since) == []


def test_unreviewed_permission_diffs_no_dir(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(nbr, "PERMISSION_DIFFS_DIR", tmp_path / "missing")
    assert nbr._unreviewed_permission_diffs(datetime.now(timezone.utc)) == []
