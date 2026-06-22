"""Tests for sms hook session-start."""
from __future__ import annotations

import json
from pathlib import Path

from .conftest import run_sms


def test_hook_emits_context_for_sms_branch(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    result = run_sms(["hook", "session-start"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "sms context" in out.lower()
    assert "feature-x" in out
    assert "Notes dir" in out


def test_hook_silent_for_non_sms_branch(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """If current branch is not in tree.json, hook prints nothing and exits 0."""
    result = run_sms(["hook", "session-start"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_hook_includes_sibling_count(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = json.loads((scratch_repo / ".git" / "sms" / "tree.json").read_text())
    parent = next(iter(t["branches"]["feature-x"]["sessions"]))
    (scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{parent}.jsonl").write_text("{}\n")
    run_sms(["fork", "--from", parent, "--no-launch"], cwd=scratch_repo)
    result = run_sms(["hook", "session-start"], cwd=scratch_repo)
    # Two sessions on branch
    assert "2" in result.stdout


def test_hook_with_cwd_argument(scratch_repo: Path, isolated_home: Path) -> None:
    """The --cwd option lets the hook resolve from a path that isn't current cwd."""
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    # Run sms hook from a different cwd, with --cwd pointing at scratch_repo
    result = run_sms(["hook", "session-start", "--cwd", str(scratch_repo)],
                     cwd=isolated_home)
    assert result.returncode == 0, result.stderr
    assert "feature-x" in result.stdout
