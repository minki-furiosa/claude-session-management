"""Tests for `sms adopt` (register a pre-existing branch)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .conftest import run_sms


def _read_tree(repo: Path) -> dict:
    return json.loads((repo / ".git" / "sms" / "tree.json").read_text())


def _checkout_existing(repo: Path, branch: str) -> None:
    """Create a real git branch the sms-free way, and switch to it."""
    subprocess.run(["git", "checkout", "-b", branch], cwd=repo,
                   check=True, capture_output=True)


def test_adopt_registers_current_branch_and_first_session(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    _checkout_existing(scratch_repo, "legacy-work")
    result = run_sms(["adopt", "--no-materialize"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr

    t = _read_tree(scratch_repo)
    assert "legacy-work" in t["branches"]
    b = t["branches"]["legacy-work"]
    assert b["parent"] is None
    assert b["state"] == "active"
    assert len(b["sessions"]) == 1
    s = next(iter(b["sessions"].values()))
    assert s["is_main"] is True
    assert s["name"] == "legacy-work"


def test_adopt_does_not_touch_git_branch(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """adopt registers the CURRENT branch; it must not create or switch branches."""
    _checkout_existing(scratch_repo, "legacy-work")
    run_sms(["adopt", "--no-materialize"], cwd=scratch_repo)
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=scratch_repo, capture_output=True, text=True,
    ).stdout.strip()
    assert branch == "legacy-work"


def test_adopt_custom_name(scratch_repo: Path, isolated_home: Path) -> None:
    _checkout_existing(scratch_repo, "legacy-work")
    run_sms(["adopt", "--name", "picking this up again", "--no-materialize"],
            cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    s = next(iter(t["branches"]["legacy-work"]["sessions"].values()))
    assert s["name"] == "picking this up again"


def test_adopt_refuses_already_tracked(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """A branch created via sms new is already tracked; adopt should refuse."""
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    result = run_sms(["adopt", "--no-materialize"], cwd=scratch_repo)
    assert result.returncode != 0
    assert "already" in result.stderr.lower()


def test_adopt_refuses_detached_head(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=scratch_repo, capture_output=True, text=True,
    ).stdout.strip()
    subprocess.run(["git", "checkout", head], cwd=scratch_repo,
                   check=True, capture_output=True)
    result = run_sms(["adopt", "--no-materialize"], cwd=scratch_repo)
    assert result.returncode != 0
    assert "detached" in result.stderr.lower()


def test_session_new_works_after_adopt(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """End-to-end: adopt an existing branch, then add more sessions to it."""
    _checkout_existing(scratch_repo, "legacy-work")
    run_sms(["adopt", "--no-materialize"], cwd=scratch_repo)
    result = run_sms(["session-new", "--no-materialize"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    t = _read_tree(scratch_repo)
    assert len(t["branches"]["legacy-work"]["sessions"]) == 2
