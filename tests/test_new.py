"""Tests for `sms new`."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .conftest import run_sms


def _read_tree(repo: Path) -> dict:
    return json.loads((repo / ".git" / "sms" / "tree.json").read_text())


def test_new_branch_creates_branch_and_tree_entry(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    result = run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr

    # git branch switched
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=scratch_repo, capture_output=True, text=True,
    ).stdout.strip()
    assert branch == "feature-x"

    # tree entry exists with parent
    t = _read_tree(scratch_repo)
    assert "feature-x" in t["branches"]
    assert t["branches"]["feature-x"]["parent"] == "main"
    assert t["branches"]["feature-x"]["state"] == "active"
    assert len(t["branches"]["feature-x"]["sessions"]) == 1


def test_new_session_is_main_and_has_label(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    result = run_sms(
        ["new", "feature-x", "--name", "initial draft", "--no-launch"],
        cwd=scratch_repo,
    )
    assert result.returncode == 0, result.stderr
    t = _read_tree(scratch_repo)
    sessions = t["branches"]["feature-x"]["sessions"]
    assert len(sessions) == 1
    s = next(iter(sessions.values()))
    assert s["is_main"] is True
    assert s["name"] == "initial draft"


def test_new_creates_symlink_in_projects_dir(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    result = run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    t = _read_tree(scratch_repo)
    uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    cwd_hash = str(scratch_repo.resolve()).replace("/", "-")
    link = isolated_home / ".claude" / "projects" / cwd_hash / f"{uuid}.jsonl"
    assert link.is_symlink()
    target = os.readlink(link)
    assert target == str(
        scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{uuid}.jsonl"
    )


def test_new_prints_uuid_with_no_launch(scratch_repo: Path, isolated_home: Path) -> None:
    result = run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    # stdout contains the UUID
    t = _read_tree(scratch_repo)
    uuid = next(iter(t["branches"]["feature-x"]["sessions"]))
    assert uuid in result.stdout


def test_new_refuses_duplicate_branch(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    result = run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    assert result.returncode != 0
    # git's own error or our own — either works, as long as it fails
    assert "feature-x" in (result.stderr + result.stdout)


def test_new_captures_parent_before_checkout(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """When run from branch X, parent should be X, not whatever HEAD is after checkout."""
    subprocess.run(
        ["git", "checkout", "-b", "feature-base"],
        cwd=scratch_repo, check=True, capture_output=True,
    )
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    assert t["branches"]["feature-x"]["parent"] == "feature-base"


def test_new_refuses_when_branch_already_in_tree_but_not_in_git(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """If tree.json has a branch but git doesn't, sms new should refuse before touching git."""
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    # Delete the git branch
    subprocess.run(["git", "checkout", "main"], cwd=scratch_repo, check=True, capture_output=True)
    subprocess.run(["git", "branch", "-D", "feature-x"], cwd=scratch_repo, check=True, capture_output=True)
    # tree.json still has feature-x
    result = run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    assert result.returncode != 0
    assert "tree.json" in result.stderr.lower()
    # Verify git was NOT touched (still on main)
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=scratch_repo, capture_output=True, text=True,
    ).stdout.strip()
    assert branch == "main"
