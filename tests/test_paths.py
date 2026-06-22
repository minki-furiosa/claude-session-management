"""Tests for path resolution helpers."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from .conftest import run_sms


def test_find_main_git_dir_in_main_repo(scratch_repo: Path) -> None:
    """In the main repo, find_main_git_dir returns <repo>/.git."""
    result = run_sms(["debug-paths"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    lines = dict(line.split("=", 1) for line in result.stdout.strip().splitlines())
    assert lines["main_git_dir"] == str(scratch_repo / ".git")


def test_find_main_git_dir_in_worktree(scratch_repo: Path, tmp_path: Path) -> None:
    """In a linked worktree, find_main_git_dir still returns the main repo's .git."""
    wt = tmp_path / "wt"
    subprocess.run(
        ["git", "worktree", "add", str(wt), "-b", "feature-x"],
        cwd=scratch_repo, check=True, capture_output=True,
    )
    result = run_sms(["debug-paths"], cwd=wt)
    assert result.returncode == 0, result.stderr
    lines = dict(line.split("=", 1) for line in result.stdout.strip().splitlines())
    assert lines["main_git_dir"] == str(scratch_repo / ".git")


def test_current_branch(scratch_repo: Path) -> None:
    result = run_sms(["debug-paths"], cwd=scratch_repo)
    lines = dict(line.split("=", 1) for line in result.stdout.strip().splitlines())
    assert lines["branch"] == "main"


def test_cwd_hash_format(scratch_repo: Path) -> None:
    result = run_sms(["debug-paths"], cwd=scratch_repo)
    lines = dict(line.split("=", 1) for line in result.stdout.strip().splitlines())
    expected = str(scratch_repo.resolve()).replace("/", "-")
    assert lines["cwd_hash"] == expected


def test_claude_projects_dir(scratch_repo: Path, isolated_home: Path) -> None:
    result = run_sms(["debug-paths"], cwd=scratch_repo)
    lines = dict(line.split("=", 1) for line in result.stdout.strip().splitlines())
    expected_hash = str(scratch_repo.resolve()).replace("/", "-")
    assert lines["projects_dir"] == str(isolated_home / ".claude" / "projects" / expected_hash)


def test_sms_root(scratch_repo: Path) -> None:
    result = run_sms(["debug-paths"], cwd=scratch_repo)
    lines = dict(line.split("=", 1) for line in result.stdout.strip().splitlines())
    assert lines["sms_root"] == str(scratch_repo / ".git" / "sms")
