"""Tests for `sms checkout`."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .conftest import run_sms


def _projects(home: Path, cwd: Path) -> Path:
    return home / ".claude" / "projects" / str(cwd.resolve()).replace("/", "-")


def test_checkout_switches_branch_and_syncs_symlinks(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    # Create feature-x, switch to main, then check it out via sms
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    t = json.loads((scratch_repo / ".git" / "sms" / "tree.json").read_text())
    x_uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    subprocess.run(["git", "checkout", "main"], cwd=scratch_repo,
                   check=True, capture_output=True)

    # Manually clean projects dir to simulate fresh state
    pd = _projects(isolated_home, scratch_repo)
    for entry in list(pd.iterdir()):
        if entry.is_symlink():
            entry.unlink()

    result = run_sms(["checkout", "feature-x"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr

    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=scratch_repo, capture_output=True, text=True,
    ).stdout.strip()
    assert branch == "feature-x"
    assert (pd / f"{x_uuid}.jsonl").is_symlink()


def test_checkout_fails_if_branch_taken_by_another_worktree(
    scratch_repo: Path, isolated_home: Path, tmp_path: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    # Create a second worktree on main before checking out feature-x in main worktree
    wt = tmp_path / "wt"
    subprocess.run(["git", "worktree", "add", str(wt), "main"],
                   cwd=scratch_repo, check=True, capture_output=True)
    # Now check out feature-x in the original worktree
    subprocess.run(["git", "checkout", "feature-x"], cwd=scratch_repo,
                   check=True, capture_output=True)
    # Now attempt sms checkout in the second worktree (should fail because feature-x is checked out elsewhere)
    result = run_sms(["checkout", "feature-x"], cwd=wt)
    assert result.returncode != 0
    # Git's error
    assert "already" in (result.stderr + result.stdout).lower()
