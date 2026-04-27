"""Tests for scripts/beat.py — happy and adverse paths."""

import json
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Import the module under test ───────────────────────────────────────────────
# Beat.py lives outside the package hierarchy; import by path.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import beat  # noqa: E402


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_state():
    """Reset module-level _state and DRY_RUN between tests."""
    beat._state = beat._State()
    original_dry_run = beat.DRY_RUN
    yield
    beat._state = beat._State()
    beat.DRY_RUN = original_dry_run


@pytest.fixture()
def tmp_project(tmp_path):
    """Minimal git-like project directory with beat-log.jsonl."""
    (tmp_path / ".git").mkdir()
    return tmp_path


@pytest.fixture()
def beat_log(tmp_project):
    return tmp_project / "beat-log.jsonl"


# ── parse_pick ─────────────────────────────────────────────────────────────────


class TestParsePick:
    def test_pick_exact(self):
        assert beat.parse_pick("PICK: 0023") == "0023"

    def test_pick_with_leading_prose(self):
        assert beat.parse_pick("After reviewing tickets, PICK: 0111") == "0111"

    def test_pick_multiline(self):
        assert beat.parse_pick("Thinking...\nPICK: 0042\nDone.") == "0042"

    def test_pick_no_space(self):
        # "PICK:0023" without space — regex requires \s* so this matches
        assert beat.parse_pick("PICK:0023") == "0023"

    def test_idle_keyword(self):
        assert beat.parse_pick("IDLE: no eligible tickets") is None

    def test_idle_case_insensitive(self):
        assert beat.parse_pick("idle: nothing to do") is None

    def test_idle_takes_precedence_over_pick(self):
        # If both appear, IDLE wins (safety bias)
        assert beat.parse_pick("IDLE: queue empty\nPICK: 0007") is None

    def test_ambiguous_no_keyword(self):
        assert beat.parse_pick("I reviewed the tickets and found nothing") is None

    def test_empty_string(self):
        assert beat.parse_pick("") is None

    def test_pick_must_be_four_digits(self):
        # Three-digit ID should not match \d{4}
        assert beat.parse_pick("PICK: 042") is None

    def test_pick_five_digits_no_match(self):
        assert beat.parse_pick("PICK: 00042") is None

    def test_dry_run_sentinel(self):
        assert beat.parse_pick("PICK: 9999") == "9999"


# ── housekeeping_needed ────────────────────────────────────────────────────────


class TestHousekeepingNeeded:
    _SHA = "abc1234567890abcdef1234567890abcdef123456"

    def test_no_commits_returns_true(self, tmp_project):
        with patch("beat.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)
            assert beat.housekeeping_needed(tmp_project) is True

    def test_recent_commit_returns_false(self, tmp_project):
        recent = f"{int(time.time()) - 3600} {self._SHA}"
        with patch("beat.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=recent + "\n", returncode=0)
            assert beat.housekeeping_needed(tmp_project) is False

    def test_old_commit_with_activity_returns_true(self, tmp_project):
        old = f"{int(time.time()) - 14 * 3600} {self._SHA}"
        with patch("beat.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout=old + "\n", returncode=0),
                MagicMock(stdout="3\n", returncode=0),
            ]
            assert beat.housekeeping_needed(tmp_project) is True

    def test_old_commit_idle_returns_false(self, tmp_project):
        old = f"{int(time.time()) - 14 * 3600} {self._SHA}"
        with patch("beat.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout=old + "\n", returncode=0),
                MagicMock(stdout="0\n", returncode=0),
            ]
            assert beat.housekeeping_needed(tmp_project) is False

    def test_safety_floor_always_runs(self, tmp_project):
        very_old = f"{int(time.time()) - 25 * 3600} {self._SHA}"
        with patch("beat.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=very_old + "\n", returncode=0)
            assert beat.housekeeping_needed(tmp_project) is True

    def test_corrupted_timestamp_returns_true(self, tmp_project):
        with patch("beat.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="not-a-number\n", returncode=0)
            assert beat.housekeeping_needed(tmp_project) is True

    def test_exactly_at_threshold_is_not_needed(self, tmp_project):
        at_threshold = (
            f"{int(time.time()) - beat.HOUSEKEEPING_INTERVAL_S + 10} {self._SHA}"
        )
        with patch("beat.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=at_threshold + "\n", returncode=0)
            assert beat.housekeeping_needed(tmp_project) is False


# ── append_beat_log ────────────────────────────────────────────────────────────


class TestAppendBeatLog:
    def test_appends_record(self, tmp_project, beat_log):
        beat.append_beat_log(
            tmp_project, {"outcome": "in_progress", "last_run_at": "t"}
        )
        records = [json.loads(line) for line in beat_log.read_text().splitlines()]
        assert records == [{"outcome": "in_progress", "last_run_at": "t"}]

    def test_appends_multiple_records(self, tmp_project, beat_log):
        beat.append_beat_log(tmp_project, {"outcome": "in_progress"})
        beat.append_beat_log(tmp_project, {"outcome": "done"})
        outcomes = [
            json.loads(line)["outcome"] for line in beat_log.read_text().splitlines()
        ]
        assert outcomes == ["in_progress", "done"]

    def test_dry_run_is_noop(self, tmp_project, beat_log):
        beat.DRY_RUN = True
        beat.append_beat_log(tmp_project, {"outcome": "done"})
        assert not beat_log.exists()


# ── finalize_beat_log ──────────────────────────────────────────────────────────


class TestFinalizeBeatLog:
    def test_replaces_trailing_in_progress(self, tmp_project, beat_log):
        beat_log.write_text(
            json.dumps({"outcome": "in_progress", "last_run_at": "t"}) + "\n"
        )
        beat.finalize_beat_log(tmp_project, {"outcome": "done", "ticket_id": "0001"})
        lines = beat_log.read_text().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["outcome"] == "done"

    def test_keeps_prior_records(self, tmp_project, beat_log):
        beat_log.write_text(
            json.dumps({"outcome": "done", "ticket_id": "0001"})
            + "\n"
            + json.dumps({"outcome": "in_progress"})
            + "\n"
        )
        beat.finalize_beat_log(tmp_project, {"outcome": "idle"})
        lines = [json.loads(line) for line in beat_log.read_text().splitlines()]
        assert len(lines) == 2
        assert lines[0]["outcome"] == "done"
        assert lines[1]["outcome"] == "idle"

    def test_creates_file_if_missing(self, tmp_project, beat_log):
        beat.finalize_beat_log(tmp_project, {"outcome": "idle"})
        # append_beat_log is called internally; dry-run=False so it writes
        assert beat_log.exists()

    def test_idempotent_second_call_ignored(self, tmp_project, beat_log):
        beat_log.write_text(json.dumps({"outcome": "in_progress"}) + "\n")
        beat.finalize_beat_log(tmp_project, {"outcome": "done"})
        beat.finalize_beat_log(tmp_project, {"outcome": "failed"})  # should be ignored
        lines = beat_log.read_text().splitlines()
        assert json.loads(lines[-1])["outcome"] == "done"

    def test_handles_pretty_printed_in_progress(self, tmp_project, beat_log):
        # Legacy records may be multi-line JSON; finalize_beat_log works on
        # compact lines it wrote itself — pretty-printed records are left as-is.
        pretty = textwrap.dedent("""\
            {
              "outcome": "done",
              "ticket_id": "0001"
            }
        """)
        # The last line of a pretty record is '}', which json.loads succeeds on
        # but .get("outcome") returns None → loop breaks → final record appended.
        beat_log.write_text(pretty)
        beat.finalize_beat_log(tmp_project, {"outcome": "idle"})
        last_line = beat_log.read_text().splitlines()[-1]
        assert json.loads(last_line)["outcome"] == "idle"

    def test_dry_run_is_noop(self, tmp_project, beat_log):
        beat.DRY_RUN = True
        beat_log.write_text(json.dumps({"outcome": "in_progress"}) + "\n")
        beat.finalize_beat_log(tmp_project, {"outcome": "done"})
        assert json.loads(beat_log.read_text().strip())["outcome"] == "in_progress"


# ── read_last_beat_record ──────────────────────────────────────────────────────


class TestReadLastBeatRecord:
    def test_returns_last_compact_record(self, tmp_project, beat_log):
        beat_log.write_text(
            json.dumps({"outcome": "done"})
            + "\n"
            + json.dumps({"outcome": "idle"})
            + "\n"
        )
        result = beat.read_last_beat_record(tmp_project)
        assert result is not None
        assert result["outcome"] == "idle"

    def test_returns_none_for_missing_file(self, tmp_project):
        result = beat.read_last_beat_record(tmp_project)
        assert result is None

    def test_returns_none_for_empty_file(self, tmp_project, beat_log):
        beat_log.write_text("")
        result = beat.read_last_beat_record(tmp_project)
        assert result is None

    def test_handles_pretty_printed_json(self, tmp_project, beat_log):
        pretty = (
            '{"outcome": "in_progress",\n  "last_run_at": "2026-01-01T00:00:00Z"\n}\n'
        )
        beat_log.write_text(pretty)
        result = beat.read_last_beat_record(tmp_project)
        assert result is not None
        assert result["outcome"] == "in_progress"


# ── run_skill (dry-run mode) ───────────────────────────────────────────────────


class TestRunSkillDryRun:
    def setup_method(self):
        beat.DRY_RUN = True

    def test_pick_ticket_returns_pick_sentinel(self, tmp_project):
        rc, result = beat.run_skill(
            "/pick-ticket", budget=0.20, timeout_s=60, cwd=tmp_project
        )
        assert rc == 0
        assert "PICK: 9999" in result

    def test_other_skill_returns_ok(self, tmp_project):
        rc, result = beat.run_skill(
            "/housekeeping", budget=0.10, timeout_s=60, cwd=tmp_project
        )
        assert rc == 0
        assert "dry-run" in result

    def test_orchestrator_returns_ok(self, tmp_project):
        rc, result = beat.run_skill(
            "/orchestrator 0001", budget=0.70, timeout_s=60, cwd=tmp_project
        )
        assert rc == 0


# ── run_skill (subprocess mode) ────────────────────────────────────────────────


class TestRunSkillSubprocess:
    def setup_method(self):
        beat.DRY_RUN = False

    def _make_popen(self, stdout_lines: list[str], returncode: int = 0):
        """Return a Popen mock that streams stdout_lines then exits."""
        import io

        proc = MagicMock()
        proc.stdout = io.StringIO("\n".join(stdout_lines) + "\n")
        proc.returncode = returncode
        proc.poll.return_value = returncode

        def fake_wait(timeout=None):
            proc.returncode = returncode

        proc.wait.side_effect = fake_wait
        return proc

    def test_extracts_result_text(self, tmp_project):
        payload = json.dumps({"type": "result", "result": "PICK: 0007"})
        proc = self._make_popen([payload])
        with patch("beat.subprocess.Popen", return_value=proc):
            rc, result = beat.run_skill(
                "/pick-ticket", budget=0.20, timeout_s=30, cwd=tmp_project
            )
        assert rc == 0
        assert "PICK: 0007" in result

    def test_ignores_non_result_lines(self, tmp_project):
        lines = [
            json.dumps({"type": "assistant", "content": "thinking..."}),
            json.dumps({"type": "result", "result": "PICK: 0042"}),
        ]
        proc = self._make_popen(lines)
        with patch("beat.subprocess.Popen", return_value=proc):
            _, result = beat.run_skill(
                "/pick-ticket", budget=0.20, timeout_s=30, cwd=tmp_project
            )
        assert result == "PICK: 0042"

    def test_timeout_returns_124(self, tmp_project):
        proc = MagicMock()
        proc.stdout = MagicMock()
        proc.stdout.__iter__ = lambda s: iter([])
        # First wait() raises TimeoutExpired; second (after terminate) succeeds.
        proc.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="claude", timeout=1),
            None,
        ]
        proc.returncode = -15
        with patch("beat.subprocess.Popen", return_value=proc):
            rc, result = beat.run_skill(
                "/pick-ticket", budget=0.20, timeout_s=1, cwd=tmp_project
            )
        assert rc == beat.TIMEOUT_EXIT_CODE
        assert result == ""

    def test_nonzero_exit_propagated(self, tmp_project):
        proc = self._make_popen([], returncode=1)
        with patch("beat.subprocess.Popen", return_value=proc):
            rc, _ = beat.run_skill(
                "/pick-ticket", budget=0.20, timeout_s=30, cwd=tmp_project
            )
        assert rc == 1

    def test_clears_current_proc_after_run(self, tmp_project):
        proc = self._make_popen([])
        with patch("beat.subprocess.Popen", return_value=proc):
            beat.run_skill("/housekeeping", budget=0.10, timeout_s=30, cwd=tmp_project)
        assert beat._state.current_proc is None

    def test_malformed_json_lines_skipped(self, tmp_project):
        lines = [
            "not json at all",
            json.dumps({"type": "result", "result": "IDLE: ok"}),
        ]
        proc = self._make_popen(lines)
        with patch("beat.subprocess.Popen", return_value=proc):
            _, result = beat.run_skill(
                "/pick-ticket", budget=0.20, timeout_s=30, cwd=tmp_project
            )
        assert result == "IDLE: ok"


# ── _orchestrate ───────────────────────────────────────────────────────────────


class TestOrchestrate:
    def setup_method(self):
        beat.DRY_RUN = False

    def _patch_run_skill(self, responses: dict):
        """responses: {skill_substr: (rc, result)}"""

        def fake_run_skill(skill, *, budget, timeout_s, cwd, project_scoped=False):
            for key, val in responses.items():
                if key in skill:
                    return val
            return (0, "")

        return patch("beat.run_skill", side_effect=fake_run_skill)

    def test_idle_path(self, tmp_project):
        with (
            patch("beat.housekeeping_needed", return_value=False),
            self._patch_run_skill({"pick-ticket": (0, "IDLE: empty queue")}),
        ):
            outcome, ticket = beat._orchestrate(beat.ProjectConfig(path=tmp_project))
        assert outcome == "idle"
        assert ticket is None

    def test_pick_and_done_path(self, tmp_project):
        with (
            patch("beat.housekeeping_needed", return_value=False),
            self._patch_run_skill(
                {
                    "pick-ticket": (0, "PICK: 0023"),
                    "orchestrator": (0, ""),
                }
            ),
        ):
            outcome, ticket = beat._orchestrate(beat.ProjectConfig(path=tmp_project))
        assert outcome == "done"
        assert ticket == "0023"

    def test_pick_ticket_timeout(self, tmp_project):
        with (
            patch("beat.housekeeping_needed", return_value=False),
            self._patch_run_skill({"pick-ticket": (beat.TIMEOUT_EXIT_CODE, "")}),
        ):
            outcome, ticket = beat._orchestrate(beat.ProjectConfig(path=tmp_project))
        assert outcome == "aborted"
        assert ticket is None

    def test_pick_ticket_nonzero_exit(self, tmp_project):
        with (
            patch("beat.housekeeping_needed", return_value=False),
            self._patch_run_skill({"pick-ticket": (1, "")}),
        ):
            outcome, ticket = beat._orchestrate(beat.ProjectConfig(path=tmp_project))
        assert outcome == "failed"
        assert ticket is None

    def test_orchestrator_timeout(self, tmp_project):
        with (
            patch("beat.housekeeping_needed", return_value=False),
            self._patch_run_skill(
                {
                    "pick-ticket": (0, "PICK: 0005"),
                    "orchestrator": (beat.TIMEOUT_EXIT_CODE, ""),
                }
            ),
        ):
            outcome, ticket = beat._orchestrate(beat.ProjectConfig(path=tmp_project))
        assert outcome == "aborted"
        assert ticket == "0005"

    def test_orchestrator_nonzero_exit(self, tmp_project):
        with (
            patch("beat.housekeeping_needed", return_value=False),
            self._patch_run_skill(
                {
                    "pick-ticket": (0, "PICK: 0005"),
                    "orchestrator": (2, ""),
                }
            ),
        ):
            outcome, ticket = beat._orchestrate(beat.ProjectConfig(path=tmp_project))
        assert outcome == "failed"
        assert ticket == "0005"

    def test_housekeeping_runs_when_needed(self, tmp_project):
        calls = []

        def fake_run_skill(skill, **kwargs):
            calls.append(skill)
            if "pick-ticket" in skill:
                return (0, "IDLE: empty")
            return (0, "")

        with (
            patch("beat.housekeeping_needed", return_value=True),
            patch("beat.run_skill", side_effect=fake_run_skill),
        ):
            beat._orchestrate(beat.ProjectConfig(path=tmp_project))

        assert any("housekeeping" in c for c in calls)

    def test_housekeeping_skipped_when_recent(self, tmp_project):
        calls = []

        def fake_run_skill(skill, **kwargs):
            calls.append(skill)
            return (0, "IDLE: empty")

        with (
            patch("beat.housekeeping_needed", return_value=False),
            patch("beat.run_skill", side_effect=fake_run_skill),
        ):
            beat._orchestrate(beat.ProjectConfig(path=tmp_project))

        assert not any("housekeeping" in c for c in calls)


# ── cross-project isolation (_claude_argv project_scoped) ─────────────────────


class TestProjectScopedIsolation:
    """Guard against cross-project ticket leakage via harness --add-dir."""

    def test_default_argv_includes_harness_add_dir(self):
        argv = beat._claude_argv("/housekeeping", 0.25)
        add_dirs = [argv[i + 1] for i, a in enumerate(argv) if a == "--add-dir"]
        assert str(beat.HARNESS_DIR) in add_dirs

    def test_project_scoped_argv_excludes_harness_add_dir(self):
        argv = beat._claude_argv("/pick-ticket", 0.50, project_scoped=True)
        add_dirs = [argv[i + 1] for i, a in enumerate(argv) if a == "--add-dir"]
        assert str(beat.HARNESS_DIR) not in add_dirs

    def test_project_scoped_argv_still_includes_project_add_dir(self):
        argv = beat._claude_argv("/pick-ticket", 0.50, project_scoped=True)
        add_dirs = [argv[i + 1] for i, a in enumerate(argv) if a == "--add-dir"]
        assert "." in add_dirs

    def test_orchestrate_passes_project_scoped_to_pick_ticket(self, tmp_project):
        recorded: list[dict] = []

        def fake_run_skill(skill, *, budget, timeout_s, cwd, project_scoped=False):
            recorded.append({"skill": skill, "project_scoped": project_scoped})
            return (0, "IDLE: empty")

        with (
            patch("beat.housekeeping_needed", return_value=False),
            patch("beat.run_skill", side_effect=fake_run_skill),
        ):
            beat._orchestrate(beat.ProjectConfig(path=tmp_project))

        pick_call = next(r for r in recorded if "pick-ticket" in r["skill"])
        assert pick_call["project_scoped"] is True

    def test_orchestrate_passes_project_scoped_to_orchestrator(self, tmp_project):
        recorded: list[dict] = []

        def fake_run_skill(skill, *, budget, timeout_s, cwd, project_scoped=False):
            recorded.append({"skill": skill, "project_scoped": project_scoped})
            if "pick-ticket" in skill:
                return (0, "PICK: 0001")
            return (0, "")

        with (
            patch("beat.housekeeping_needed", return_value=False),
            patch("beat.run_skill", side_effect=fake_run_skill),
        ):
            beat._orchestrate(beat.ProjectConfig(path=tmp_project))

        oc_call = next(r for r in recorded if "orchestrator" in r["skill"])
        assert oc_call["project_scoped"] is True

    def test_orchestrate_does_not_scope_housekeeping(self, tmp_project):
        recorded: list[dict] = []

        def fake_run_skill(skill, *, budget, timeout_s, cwd, project_scoped=False):
            recorded.append({"skill": skill, "project_scoped": project_scoped})
            return (0, "IDLE: empty")

        with (
            patch("beat.housekeeping_needed", return_value=True),
            patch("beat.run_skill", side_effect=fake_run_skill),
        ):
            beat._orchestrate(beat.ProjectConfig(path=tmp_project))

        hk_call = next(r for r in recorded if "housekeeping" in r["skill"])
        assert hk_call["project_scoped"] is False


# ── per-project lock ──────────────────────────────────────────────────────────


class TestPerProjectLock:
    def test_lockfile_per_project_name(self, tmp_path):
        proj_a = tmp_path / "alpha"
        proj_b = tmp_path / "beta"
        assert beat._lockfile(proj_a).name != beat._lockfile(proj_b).name

    def test_lockfile_contains_project_name(self, tmp_path):
        project = tmp_path / "myproject"
        assert "myproject" in beat._lockfile(project).name

    def test_lockfile_parent_is_lock_dir(self, tmp_path):
        project = tmp_path / "p"
        assert beat._lockfile(project).parent == beat._LOCK_DIR

    def test_already_locked_exits_zero(self, tmp_project, tmp_path):
        """A project already locked by another beat instance causes exit(0)."""
        fake_lock_dir = tmp_path / "locks"
        with (
            patch("beat.signal.signal"),
            patch("beat._setup_env"),
            patch.object(beat, "LOGDIR", tmp_path / "logs"),
            patch("beat._pick_project", return_value=(0, beat.ProjectConfig(path=tmp_project))),
            patch.object(beat, "_LOCK_DIR", fake_lock_dir),
            patch("beat.fcntl.flock", side_effect=BlockingIOError),
            pytest.raises(SystemExit) as exc_info,
        ):
            beat.main()
        assert exc_info.value.code == 0


# ── crash recovery ─────────────────────────────────────────────────────────────


class TestCrashRecovery:
    def test_recent_in_progress_triggers_aborted(self, tmp_project, beat_log):
        from datetime import datetime

        recent_ts = "2026-04-25T15:00:00Z"
        beat_log.write_text(
            json.dumps({"outcome": "in_progress", "last_run_at": recent_ts}) + "\n"
        )
        recent_epoch = datetime.fromisoformat(
            recent_ts.replace("Z", "+00:00")
        ).timestamp()

        with (
            patch("beat.read_last_beat_record") as mock_last,
            patch("beat.append_beat_log") as mock_append,
            patch("beat.time.time", return_value=recent_epoch + 60),  # 1 min later
        ):
            mock_last.return_value = {
                "outcome": "in_progress",
                "last_run_at": recent_ts,
            }
            last = mock_last(tmp_project)
            if last and last.get("outcome") == "in_progress":
                last_at = last.get("last_run_at", "1970-01-01T00:00:00Z")
                last_ep = datetime.fromisoformat(
                    last_at.replace("Z", "+00:00")
                ).timestamp()
                if (recent_epoch + 60 - last_ep) < beat.CRASH_RECOVERY_WINDOW_S:
                    mock_append(
                        tmp_project,
                        {
                            "outcome": "aborted",
                            "diagnostics": "crash/SIGKILL recovery — previous run never completed spin-down",
                        },
                    )

        mock_append.assert_called_once()
        call_record = mock_append.call_args[0][1]
        assert call_record["outcome"] == "aborted"
        assert "crash" in call_record["diagnostics"]

    def test_old_in_progress_does_not_trigger_recovery(self, tmp_project):
        from datetime import datetime

        old_ts = "2026-04-25T00:00:00Z"
        old_epoch = datetime.fromisoformat(old_ts.replace("Z", "+00:00")).timestamp()
        now = old_epoch + 15 * 3600  # 15 hours after spin-in

        last_epoch = datetime.fromisoformat(old_ts.replace("Z", "+00:00")).timestamp()
        elapsed = now - last_epoch
        assert elapsed >= beat.CRASH_RECOVERY_WINDOW_S


# ── spin-down completeness ─────────────────────────────────────────────────────


class TestSpinDown:
    def test_finalize_always_called_on_normal_exit(self, tmp_project, beat_log):
        beat_log.write_text(json.dumps({"outcome": "in_progress"}) + "\n")
        with (
            patch("beat.housekeeping_needed", return_value=False),
            patch(
                "beat.run_skill",
                side_effect=lambda s, **kw: (0, "IDLE: empty" if "pick" in s else ""),
            ),
        ):
            beat._state.project = tmp_project
            beat._state.final_written = False
            beat.DRY_RUN = False
            outcome, ticket = beat._orchestrate(beat.ProjectConfig(path=tmp_project))
            beat.finalize_beat_log(
                tmp_project,
                {
                    "last_run_at": "t",
                    "ticket_id": ticket,
                    "outcome": outcome,
                    "duration_s": 0,
                },
            )
        last_line = beat_log.read_text().splitlines()[-1]
        assert json.loads(last_line)["outcome"] == "idle"
