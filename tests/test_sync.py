"""Tests for `sms sync`."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .conftest import run_sms


def _projects(home: Path, cwd: Path) -> Path:
    return home / ".claude" / "projects" / str(cwd.resolve()).replace("/", "-")


def _canonical(repo: Path, branch: str, uuid: str) -> Path:
    return repo / ".git" / "sms" / "sessions" / branch / f"{uuid}.jsonl"


def test_sync_creates_missing_symlinks_for_current_branch(
    scratch_repo: Path, isolated_home: Path, tmp_path: Path,
) -> None:
    """Branch was checked out manually in worktree B; sms sync populates the symlinks."""
    # 1. In main worktree A, create feature-x with a session
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = json.loads((scratch_repo / ".git" / "sms" / "tree.json").read_text())
    uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    # 2. Move feature-x to a second worktree B (simulated: leave A on main, add a worktree)
    subprocess.run(["git", "checkout", "main"], cwd=scratch_repo,
                   check=True, capture_output=True)
    # Remove the worktree-A symlink (we're simulating "branch moved away")
    a_link = _projects(isolated_home, scratch_repo) / f"{uuid}.jsonl"
    if a_link.is_symlink():
        a_link.unlink()

    wt_b = tmp_path / "wtB"
    subprocess.run(
        ["git", "worktree", "add", str(wt_b), "feature-x"],
        cwd=scratch_repo, check=True, capture_output=True,
    )

    # 3. Before sync: B's projects dir is empty
    b_link = _projects(isolated_home, wt_b) / f"{uuid}.jsonl"
    assert not b_link.exists()

    # 4. After sync: B has the symlink
    result = run_sms(["sync"], cwd=wt_b)
    assert result.returncode == 0, result.stderr
    assert b_link.is_symlink()
    assert os.readlink(b_link) == str(_canonical(scratch_repo, "feature-x", uuid))


def test_sync_removes_stale_symlinks_pointing_to_other_branches(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """If projects dir has a symlink pointing to branch B but current branch is A, remove it."""
    # Create feature-x and feature-y, with a session on each
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = json.loads((scratch_repo / ".git" / "sms" / "tree.json").read_text())
    x_uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    # Back to main, then create feature-y
    subprocess.run(["git", "checkout", "main"], cwd=scratch_repo,
                   check=True, capture_output=True)
    run_sms(["new", "feature-y", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = json.loads((scratch_repo / ".git" / "sms" / "tree.json").read_text())
    y_uuid = next(iter(t["branches"]["feature-y"]["sessions"]))

    # Remove feature-x's symlink (simulating that the user manually ran sync on feature-y
    # which cleared the projects dir of cross-branch symlinks, then manually restored
    # feature-x's symlink from a backup or it lingered from a previous session).
    pd = _projects(isolated_home, scratch_repo)
    x_link = pd / f"{x_uuid}.jsonl"
    if x_link.is_symlink():
        x_link.unlink()
    # Now manually create a stale symlink pointing to feature-x (simulating leftover state)
    x_link.symlink_to(_canonical(scratch_repo, "feature-x", x_uuid))
    assert x_link.is_symlink()

    result = run_sms(["sync"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr

    # feature-y's symlink stays, feature-x's is gone
    assert (pd / f"{y_uuid}.jsonl").is_symlink()
    assert not (pd / f"{x_uuid}.jsonl").exists()


def test_sync_is_idempotent(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    # Capture state
    pd = _projects(isolated_home, scratch_repo)
    before = sorted((p.name, os.readlink(p)) for p in pd.iterdir() if p.is_symlink())
    for _ in range(3):
        assert run_sms(["sync"], cwd=scratch_repo).returncode == 0
    after = sorted((p.name, os.readlink(p)) for p in pd.iterdir() if p.is_symlink())
    assert before == after


def test_sync_noop_on_non_sms_branch(scratch_repo: Path, isolated_home: Path) -> None:
    """If current branch has no tree.json entry, sync does nothing and exits 0."""
    subprocess.run(["git", "checkout", "-b", "untracked"],
                   cwd=scratch_repo, check=True, capture_output=True)
    result = run_sms(["sync"], cwd=scratch_repo)
    assert result.returncode == 0
