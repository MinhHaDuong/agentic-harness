#!/usr/bin/env python3
"""Per-project state probe. JSON on stdout, exit 0 always."""

import json
import subprocess
import sys
import time
from pathlib import Path

THRESHOLD_HOURS = 12.0


def run(args, cwd):
    return subprocess.run(args, capture_output=True, text=True, check=False, cwd=cwd)


def git_state(project):
    branch_r = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], project)
    branch = branch_r.stdout.strip() if branch_r.returncode == 0 else None

    porcelain = run(["git", "status", "--porcelain"], project)
    clean = porcelain.returncode == 0 and porcelain.stdout.strip() == ""

    lr = run(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"], project)
    ahead, behind = 0, 0
    if lr.returncode == 0:
        parts = lr.stdout.strip().split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])

    return {"branch": branch, "clean": clean, "ahead": ahead, "behind": behind}


def housekeeping_state(project):
    br = run(["git", "branch", "--list", "claude/housekeeping-*"], project)
    branches = [
        line.strip().lstrip("* ") for line in br.stdout.splitlines() if line.strip()
    ]
    hk_branch = branches[0] if branches else None

    log_r = run(["git", "log", "--grep=housekeeping", "-1", "--format=%ct"], project)
    ts_raw = log_r.stdout.strip()
    last_ts = None
    age_hours = None
    if ts_raw:
        try:
            epoch = int(ts_raw)
            last_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))
            age_hours = round((time.time() - epoch) / 3600, 1)
        except ValueError:
            pass

    if hk_branch:
        state = "tidying"
    elif last_ts is None or (age_hours is not None and age_hours > THRESHOLD_HOURS):
        state = "needed"
    else:
        state = "clean"

    return {
        "state": state,
        "branch": hk_branch,
        "last_commit_ts": last_ts,
        "age_hours": age_hours,
    }


def ticket_state(project):
    tickets_dir = project / "tickets"
    if not tickets_dir.is_dir():
        return {
            "ready": None,
            "open": None,
            "ready_ids": [],
            "error": "no tickets/ directory",
        }

    try:
        r = run(["erg", "ready", "--json", str(tickets_dir)], project)
        if r.returncode != 0:
            return {
                "ready": None,
                "open": None,
                "ready_ids": [],
                "error": f"erg failed: {r.stderr.strip()}",
            }
        ready_list = json.loads(r.stdout)
    except FileNotFoundError:
        erg_files = list(tickets_dir.glob("*.erg"))
        open_count = 0
        for f in erg_files:
            text = f.read_text(errors="replace")
            if not any(line.startswith("Closed:") for line in text.splitlines()[:10]):
                open_count += 1
        return {
            "ready": None,
            "open": open_count,
            "ready_ids": [],
            "error": "erg not found",
        }

    ready_ids = [t["id"] for t in ready_list]

    erg_files = list(tickets_dir.glob("*.erg"))
    open_count = 0
    for f in erg_files:
        text = f.read_text(errors="replace")
        if not any(line.startswith("Closed:") for line in text.splitlines()[:10]):
            open_count += 1

    return {"ready": len(ready_ids), "open": open_count, "ready_ids": ready_ids}


def test_state(project):
    makefile = project / "Makefile"
    if makefile.exists():
        content = makefile.read_text(errors="replace")
        if "check-fast" in content:
            target = "check-fast"
        elif "test" in content:
            target = "test"
        else:
            return {
                "runner": "none",
                "status": "skip",
                "detail": "no test target in Makefile",
            }
        r = run(["make", target], project)
        return {
            "runner": "make",
            "status": "pass" if r.returncode == 0 else "fail",
            "detail": r.stdout.strip().splitlines()[-1]
            if r.stdout.strip()
            else r.stderr.strip().splitlines()[-1]
            if r.stderr.strip()
            else "",
        }

    if (project / "pyproject.toml").exists() or (project / "setup.py").exists():
        r = run(["pytest", "--tb=no", "-q"], project)
        if r.returncode != 127:
            last_line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
            return {
                "runner": "pytest",
                "status": "pass" if r.returncode == 0 else "fail",
                "detail": last_line,
            }

    if (project / "package.json").exists():
        r = run(["npm", "test"], project)
        return {
            "runner": "npm",
            "status": "pass" if r.returncode == 0 else "fail",
            "detail": r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "",
        }

    return {"runner": "none", "status": "skip", "detail": "no test runner detected"}


def pr_state(project):
    r = run(
        ["gh", "pr", "list", "--json", "number,title,headRefName", "--limit", "50"],
        project,
    )
    if r.returncode != 0:
        return {
            "open": None,
            "items": [],
            "error": f"gh unavailable: {r.stderr.strip()[:80]}",
        }
    try:
        prs = json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return {"open": None, "items": [], "error": "gh output parse error"}
    items = [
        {"number": p["number"], "title": p["title"], "branch": p["headRefName"]}
        for p in prs
    ]
    return {"open": len(items), "items": items}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: project-state.py <project-path> [--full]"}))
        sys.exit(0)

    project = Path(sys.argv[1]).expanduser().resolve()
    full = "--full" in sys.argv

    out = {"path": str(project)}

    try:
        out["git"] = git_state(project)
        out["housekeeping"] = housekeeping_state(project)
        out["tickets"] = ticket_state(project)

        if full:
            out["tests"] = test_state(project)
            out["prs"] = pr_state(project)
    except Exception as e:
        out["error"] = repr(e)

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
