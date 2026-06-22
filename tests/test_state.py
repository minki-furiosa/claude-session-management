"""Tests for sms mark-merged / backlog / activate."""
from __future__ import annotations

import json
from pathlib import Path

from .conftest import run_sms


def _state(repo: Path, branch: str) -> str:
    t = json.loads((repo / ".git" / "sms" / "tree.json").read_text())
    return t["branches"][branch]["state"]


def test_mark_merged_default_branch(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    assert run_sms(["mark-merged"], cwd=scratch_repo).returncode == 0
    assert _state(scratch_repo, "feature-x") == "merged"


def test_mark_merged_named_branch(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    import subprocess
    subprocess.run(["git", "checkout", "main"], cwd=scratch_repo,
                   check=True, capture_output=True)
    assert run_sms(["mark-merged", "feature-x"], cwd=scratch_repo).returncode == 0
    assert _state(scratch_repo, "feature-x") == "merged"


def test_backlog_and_activate(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    assert run_sms(["backlog"], cwd=scratch_repo).returncode == 0
    assert _state(scratch_repo, "feature-x") == "backlog"
    assert run_sms(["activate"], cwd=scratch_repo).returncode == 0
    assert _state(scratch_repo, "feature-x") == "active"
