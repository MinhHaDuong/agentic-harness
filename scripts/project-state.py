#!/usr/bin/env python3
"""Per-project state probe. JSON on stdout, exit 0 always."""

import json
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

THRESHOLD_HOURS = 12.0


def run(args, cwd):
    return subprocess.run(args, capture_output=True, text=True, check=False, cwd=cwd)


def _default_branch(project):
    r = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], project)
    return r.stdout.strip().removeprefix("origin/") if r.returncode == 0 else "main"


def git_state(project):
    branch_r = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], project)
    branch = branch_r.stdout.strip() if branch_r.returncode == 0 else None

    porcelain = run(["git", "status", "--porcelain"], project)
    clean = porcelain.returncode == 0 and porcelain.stdout.strip() == ""
    dirty_files = (
        [line.strip() for line in porcelain.stdout.splitlines() if line.strip()]
        if not clean
        else []
    )

    lr = run(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"], project)
    ahead, behind = 0, 0
    if lr.returncode == 0:
        parts = lr.stdout.strip().split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])

    log_r = run(
        ["git", "log", "--since=12 hours ago", "--format=%H\t%ct\t%s"],
        project,
    )
    now = time.time()
    recent_commits = []
    for line in log_r.stdout.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            h, ct, subject = parts
            try:
                age_minutes = int((now - int(ct)) / 60)
            except ValueError:
                age_minutes = -1
            recent_commits.append(
                {"hash": h[:8], "subject": subject, "age_minutes": age_minutes}
            )

    return {
        "branch": branch,
        "clean": clean,
        "dirty_files": dirty_files,
        "ahead": ahead,
        "behind": behind,
        "recent_commits": recent_commits,
    }


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
        "last_housekeeping_ts": last_ts,
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

    erg_bin = shutil.which("erg") or str(project / "tickets/tools/go/erg")

    try:
        r = run([erg_bin, "ready", "--json", str(tickets_dir)], project)
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


def branch_state(project):
    default = _default_branch(project)

    local_r = run(["git", "branch", "--format=%(refname:short)"], project)
    remote_r = run(["git", "branch", "-r", "--format=%(refname:short)"], project)

    local = [b.strip() for b in local_r.stdout.splitlines() if b.strip()]
    remote = [b.strip() for b in remote_r.stdout.splitlines() if b.strip()]
    non_default = [b for b in local if b != default]

    def _count(branch):
        r = run(["git", "rev-list", "--count", f"{default}..{branch}"], project)
        try:
            return int(r.stdout.strip())
        except ValueError:
            return 0

    if non_default:
        with ThreadPoolExecutor(max_workers=min(8, len(non_default))) as pool:
            counts = list(pool.map(_count, non_default))
    else:
        counts = []

    details = [
        {"name": b, "commits_beyond_default": c} for b, c in zip(non_default, counts)
    ]

    return {"local": local, "remote": remote, "details": details}


def worktree_state(project):
    r = run(["git", "worktree", "list", "--porcelain"], project)
    if r.returncode != 0:
        return []

    worktrees: list[dict] = []
    current: dict = {}
    for line in r.stdout.splitlines():
        if not line:
            if current:
                worktrees.append(current)
                current = {}
        elif line.startswith("worktree "):
            current["path"] = line[9:]
        elif line.startswith("HEAD "):
            current["head"] = line[5:][:8]
        elif line.startswith("branch "):
            current["branch"] = line[7:].removeprefix("refs/heads/")
        elif line == "locked":
            current["locked"] = True
            current["lock_reason"] = ""
        elif line.startswith("locked "):
            current["locked"] = True
            current["lock_reason"] = line[7:]
        elif line == "detached":
            current["branch"] = None
        elif line == "bare":
            current["bare"] = True
    if current:
        worktrees.append(current)

    return worktrees


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
        try:
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
        except FileNotFoundError:
            return {"runner": "make", "status": "skip", "detail": "make not found"}

    if (project / "pyproject.toml").exists() or (project / "setup.py").exists():
        try:
            r = run(["pytest", "--tb=no", "-q"], project)
            last_line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
            return {
                "runner": "pytest",
                "status": "pass" if r.returncode == 0 else "fail",
                "detail": last_line,
            }
        except FileNotFoundError:
            return {"runner": "pytest", "status": "skip", "detail": "pytest not found"}

    if (project / "package.json").exists():
        try:
            r = run(["npm", "test"], project)
            return {
                "runner": "npm",
                "status": "pass" if r.returncode == 0 else "fail",
                "detail": r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "",
            }
        except FileNotFoundError:
            return {"runner": "npm", "status": "skip", "detail": "npm not found"}

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
    import argparse

    parser = argparse.ArgumentParser(
        description="Per-project state probe. JSON on stdout, exit 0 always."
    )
    parser.add_argument("path", help="Project path")
    parser.add_argument(
        "--tests", action="store_true", help="Run test suite (may be slow)"
    )
    args = parser.parse_args()

    project = Path(args.path).expanduser().resolve()

    out = {"path": str(project)}

    collectors: dict = {
        "git": git_state,
        "housekeeping": housekeeping_state,
        "tickets": ticket_state,
        "branches": branch_state,
        "worktrees": worktree_state,
        "prs": pr_state,
    }

    with ThreadPoolExecutor(max_workers=len(collectors)) as pool:
        futures = {key: pool.submit(fn, project) for key, fn in collectors.items()}
        for key, future in futures.items():
            try:
                out[key] = future.result()
            except Exception as e:
                out[key] = {"error": repr(e)}

    if args.tests:
        try:
            out["tests"] = test_state(project)
        except Exception as e:
            out["tests"] = {"error": repr(e)}
    else:
        out["tests"] = {
            "runner": "none",
            "status": "skip",
            "detail": "pass --tests to include",
        }

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
