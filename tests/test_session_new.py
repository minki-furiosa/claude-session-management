"""Tests for `sms session-new`."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .conftest import run_sms


def _read_tree(repo: Path) -> dict:
    return json.loads((repo / ".git" / "sms" / "tree.json").read_text())


def test_session_new_attaches_to_current_branch(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """session-new adds a sub session to the current sms-tracked branch."""
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    main_uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    result = run_sms(["session-new", "--name", "blank work", "--no-materialize"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    new_uuid = result.stdout.strip().splitlines()[-1]

    t = _read_tree(scratch_repo)
    sessions = t["branches"]["feature-x"]["sessions"]
    assert new_uuid in sessions
    assert sessions[new_uuid]["is_main"] is False
    assert sessions[new_uuid]["parent_uuid"] is None
    assert sessions[new_uuid]["name"] == "blank work"
    # main is unchanged
    assert sessions[main_uuid]["is_main"] is True


def test_session_new_default_name_numbered(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """Without --name, sub-sessions are numbered: 'branch (2)', 'branch (3)', ..."""
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    r1 = run_sms(["session-new", "--no-materialize"], cwd=scratch_repo)
    u1 = r1.stdout.strip().splitlines()[-1]
    r2 = run_sms(["session-new", "--no-materialize"], cwd=scratch_repo)
    u2 = r2.stdout.strip().splitlines()[-1]

    t = _read_tree(scratch_repo)
    sessions = t["branches"]["feature-x"]["sessions"]
    assert sessions[u1]["name"] == "feature-x (2)"
    assert sessions[u2]["name"] == "feature-x (3)"


def test_session_new_creates_symlink(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """session-new creates a (dangling) symlink in the projects dir. Materialize is
    skipped — the canonical file is created by claude when the session is opened."""
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    result = run_sms(["session-new", "--no-materialize"], cwd=scratch_repo)
    new_uuid = result.stdout.strip().splitlines()[-1]

    cwd_hash = str(scratch_repo.resolve()).replace("/", "-")
    link = isolated_home / ".claude" / "projects" / cwd_hash / f"{new_uuid}.jsonl"
    assert link.is_symlink()


def test_session_new_refuses_on_untracked_branch(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """Branch must be sms-tracked. Plain main isn't, so error."""
    result = run_sms(["session-new", "--no-materialize"], cwd=scratch_repo)
    assert result.returncode != 0
    assert "not sms-tracked" in result.stderr.lower() or "sms new" in result.stderr.lower()


def test_session_new_refuses_on_detached_head(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=scratch_repo, capture_output=True, text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "checkout", head], cwd=scratch_repo, check=True, capture_output=True,
    )
    result = run_sms(["session-new", "--no-materialize"], cwd=scratch_repo)
    assert result.returncode != 0
    assert "detached" in result.stderr.lower()
