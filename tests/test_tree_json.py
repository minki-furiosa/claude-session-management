"""Tests for tree.json read/write."""
from __future__ import annotations

import json
from pathlib import Path

from .conftest import run_sms


def _read_tree(repo: Path) -> dict:
    return json.loads((repo / ".git" / "sms" / "tree.json").read_text())


def test_empty_tree_load(scratch_repo: Path, isolated_home: Path) -> None:
    """First mutation creates tree.json with empty branches dict."""
    result = run_sms(["debug-tree", "init"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    tree = _read_tree(scratch_repo)
    assert tree == {"branches": {}}


def test_add_branch(scratch_repo: Path, isolated_home: Path) -> None:
    result = run_sms(["debug-tree", "add-branch", "feature-x", "main"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    tree = _read_tree(scratch_repo)
    b = tree["branches"]["feature-x"]
    assert b["parent"] == "main"
    assert b["state"] == "active"
    assert b["sessions"] == {}
    assert "created_at" in b


def test_add_session(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["debug-tree", "add-branch", "feature-x", "main"], cwd=scratch_repo)
    result = run_sms(
        ["debug-tree", "add-session",
         "feature-x", "11111111-1111-1111-1111-111111111111", "first", "true"],
        cwd=scratch_repo,
    )
    assert result.returncode == 0, result.stderr
    tree = _read_tree(scratch_repo)
    s = tree["branches"]["feature-x"]["sessions"]["11111111-1111-1111-1111-111111111111"]
    assert s["name"] == "first"
    assert s["is_main"] is True
    assert s["parent_uuid"] is None


def test_set_main_flips_flags(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["debug-tree", "add-branch", "feature-x", "main"], cwd=scratch_repo)
    run_sms(["debug-tree", "add-session", "feature-x",
             "11111111-1111-1111-1111-111111111111", "a", "true"], cwd=scratch_repo)
    run_sms(["debug-tree", "add-session", "feature-x",
             "22222222-2222-2222-2222-222222222222", "b", "false"], cwd=scratch_repo)

    result = run_sms(["debug-tree", "set-main", "feature-x",
                      "22222222-2222-2222-2222-222222222222"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    tree = _read_tree(scratch_repo)
    sessions = tree["branches"]["feature-x"]["sessions"]
    assert sessions["11111111-1111-1111-1111-111111111111"]["is_main"] is False
    assert sessions["22222222-2222-2222-2222-222222222222"]["is_main"] is True


def test_set_state(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["debug-tree", "add-branch", "feature-x", "main"], cwd=scratch_repo)
    result = run_sms(["debug-tree", "set-state", "feature-x", "merged"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    tree = _read_tree(scratch_repo)
    assert tree["branches"]["feature-x"]["state"] == "merged"


def test_corrupted_tree_does_not_silently_overwrite(scratch_repo: Path, isolated_home: Path) -> None:
    """A truncated/invalid tree.json causes an error, not a silent rewrite."""
    sms_dir = scratch_repo / ".git" / "sms"
    sms_dir.mkdir(parents=True)
    (sms_dir / "tree.json").write_text("not json {")
    result = run_sms(["debug-tree", "init"], cwd=scratch_repo)
    assert result.returncode == 2
    assert "tree.json" in result.stderr.lower()
