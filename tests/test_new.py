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
    result = run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr

    # git branch switched
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=scratch_repo, capture_output=True, text=True,
    ).stdout.strip()
    assert branch == "feature-x"

    # tree entry exists. main is NOT in sms tree → parent is None (root branch).
    t = _read_tree(scratch_repo)
    assert "feature-x" in t["branches"]
    assert t["branches"]["feature-x"]["parent"] is None
    assert t["branches"]["feature-x"]["state"] == "active"
    assert len(t["branches"]["feature-x"]["sessions"]) == 1


def test_new_session_is_main_and_has_label(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    result = run_sms(
        ["new", "feature-x", "--name", "initial draft", "--no-launch", "--no-materialize"],
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
    result = run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
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
    result = run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    # stdout contains the UUID
    t = _read_tree(scratch_repo)
    uuid = next(iter(t["branches"]["feature-x"]["sessions"]))
    assert uuid in result.stdout


def test_new_no_launch_default(scratch_repo: Path, isolated_home: Path) -> None:
    """Without --launch the command returns cleanly (does NOT exec claude).
    Materialize is skipped here so the test doesn't shell out to claude.
    """
    result = run_sms(["new", "feature-x", "--no-materialize"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr


def test_new_refuses_duplicate_branch(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    result = run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    assert result.returncode != 0
    # git's own error or our own — either works, as long as it fails
    assert "feature-x" in (result.stderr + result.stdout)


def test_new_parent_is_none_when_current_branch_not_in_sms_tree(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """sms tree's parent encodes sms-managed lineage. If the current git branch
    isn't sms-tracked, the new branch has no sms parent (orphan / root)."""
    subprocess.run(
        ["git", "checkout", "-b", "feature-base"],
        cwd=scratch_repo, check=True, capture_output=True,
    )
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    assert t["branches"]["feature-x"]["parent"] is None


def test_new_parent_set_when_current_branch_is_in_sms_tree(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """If the current branch IS sms-tracked, parent is captured for the new branch."""
    run_sms(["new", "feature-a", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    # Now on feature-a, which is in sms tree.
    run_sms(["new", "feature-b", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    assert t["branches"]["feature-b"]["parent"] == "feature-a"


def test_new_parent_is_none_on_detached_head(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """Detached HEAD is allowed; parent is None (sms-tree root)."""
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=scratch_repo, capture_output=True, text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "checkout", head], cwd=scratch_repo, check=True, capture_output=True,
    )
    result = run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    t = _read_tree(scratch_repo)
    assert t["branches"]["feature-x"]["parent"] is None


def test_new_default_name_is_branch(scratch_repo: Path, isolated_home: Path) -> None:
    """Without --name, the first session is named after the branch."""
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    s = next(iter(t["branches"]["feature-x"]["sessions"].values()))
    assert s["name"] == "feature-x"


def test_new_refuses_when_branch_already_in_tree_but_not_in_git(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """If tree.json has a branch but git doesn't, sms new should refuse before touching git."""
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    # Delete the git branch
    subprocess.run(["git", "checkout", "main"], cwd=scratch_repo, check=True, capture_output=True)
    subprocess.run(["git", "branch", "-D", "feature-x"], cwd=scratch_repo, check=True, capture_output=True)
    # tree.json still has feature-x
    result = run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    assert result.returncode != 0
    assert "tree.json" in result.stderr.lower()
    # Verify git was NOT touched (still on main)
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=scratch_repo, capture_output=True, text=True,
    ).stdout.strip()
    assert branch == "main"
