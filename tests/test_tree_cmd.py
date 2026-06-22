"""Tests for `sms tree`."""
from __future__ import annotations

from pathlib import Path

from .conftest import run_sms


def test_tree_renders_root_branch(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    result = run_sms(["tree"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    assert "feature-x" in result.stdout


def test_tree_indents_children(scratch_repo: Path, isolated_home: Path) -> None:
    """feature-x from main; feature-y from feature-x → y shown indented under x."""
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    run_sms(["new", "feature-y", "--no-launch"], cwd=scratch_repo)
    result = run_sms(["tree"], cwd=scratch_repo)
    lines = result.stdout.splitlines()
    x_line = next(i for i, l in enumerate(lines) if "feature-x" in l)
    y_line = next(i for i, l in enumerate(lines) if "feature-y" in l)
    # feature-y comes after feature-x and is more indented
    assert y_line > x_line
    assert lines[y_line].startswith(" ")
    assert lines[y_line].lstrip() != lines[y_line]


def test_tree_hides_merged_and_backlog_by_default(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    run_sms(["debug-tree", "set-state", "feature-x", "merged"], cwd=scratch_repo)
    result = run_sms(["tree"], cwd=scratch_repo)
    assert "feature-x" not in result.stdout
    result_all = run_sms(["tree", "--all"], cwd=scratch_repo)
    assert "feature-x" in result_all.stdout
    assert "merged" in result_all.stdout
