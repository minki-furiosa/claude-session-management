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
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    main_uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    result = run_sms(["session-new", "--name", "blank work"], cwd=scratch_repo)
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


def test_session_new_creates_symlink_and_seeded_jsonl(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    result = run_sms(["session-new"], cwd=scratch_repo)
    new_uuid = result.stdout.strip().splitlines()[-1]

    cwd_hash = str(scratch_repo.resolve()).replace("/", "-")
    link = isolated_home / ".claude" / "projects" / cwd_hash / f"{new_uuid}.jsonl"
    assert link.is_symlink()

    canonical = scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{new_uuid}.jsonl"
    assert canonical.exists()
    entry = json.loads(canonical.read_text().splitlines()[0])
    assert entry["sessionId"] == new_uuid


def test_session_new_refuses_on_untracked_branch(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """Branch must be sms-tracked. Plain main isn't, so error."""
    result = run_sms(["session-new"], cwd=scratch_repo)
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
    result = run_sms(["session-new"], cwd=scratch_repo)
    assert result.returncode != 0
    assert "detached" in result.stderr.lower()
