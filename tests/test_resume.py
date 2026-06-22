"""Tests for `sms resume`."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .conftest import run_sms


def _read_tree(repo: Path) -> dict:
    return json.loads((repo / ".git" / "sms" / "tree.json").read_text())


def test_resume_resolves_by_prefix(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    uuid = next(iter(_read_tree(scratch_repo)["branches"]["feature-x"]["sessions"]))
    prefix = uuid[:8]
    result = run_sms(["resume", prefix, "--no-launch"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    assert uuid in result.stdout


def test_resume_errors_on_ambiguous_prefix(scratch_repo: Path, isolated_home: Path) -> None:
    """Two sessions sharing a UUID prefix → resume by that prefix is ambiguous."""
    # Create branch + first session via `new`, then inject a second session
    # with a deterministically-shared UUID prefix via debug-tree.
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    first = next(iter(t["branches"]["feature-x"]["sessions"]))
    second = first[:8] + "-0000-0000-0000-000000000000"
    r = run_sms(["debug-tree", "add-session", "feature-x", second, "sibling", "false"],
                cwd=scratch_repo)
    assert r.returncode == 0, r.stderr
    result = run_sms(["resume", first[:8], "--no-launch"], cwd=scratch_repo)
    assert result.returncode != 0
    assert "ambig" in result.stderr.lower() or "multiple" in result.stderr.lower()


def test_resume_errors_on_unknown_uuid(scratch_repo: Path, isolated_home: Path) -> None:
    result = run_sms(["resume", "ffffffff-ffff-ffff-ffff-ffffffffffff", "--no-launch"],
                     cwd=scratch_repo)
    assert result.returncode != 0
    assert "no session" in result.stderr.lower() or "not found" in result.stderr.lower()


def test_resume_errors_when_branch_not_in_current_worktree(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    uuid = next(iter(_read_tree(scratch_repo)["branches"]["feature-x"]["sessions"]))
    subprocess.run(["git", "checkout", "main"], cwd=scratch_repo,
                   check=True, capture_output=True)
    result = run_sms(["resume", uuid, "--no-launch"], cwd=scratch_repo)
    assert result.returncode != 0
    assert "not checked out" in result.stderr.lower()
