"""Tests for `sms sessions`."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .conftest import run_sms


def test_sessions_lists_main_and_subs(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["new", "feature-x", "--name", "main label", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = json.loads((scratch_repo / ".git" / "sms" / "tree.json").read_text())
    parent = next(iter(t["branches"]["feature-x"]["sessions"]))
    (scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{parent}.jsonl").write_text("{}\n")
    run_sms(["fork", "--from", parent, "--name", "sub", "--no-launch"], cwd=scratch_repo)

    result = run_sms(["sessions"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr

    lines = [l for l in result.stdout.splitlines() if l.strip()]
    assert len(lines) == 2
    main_lines = [l for l in lines if l.startswith("*")]
    assert len(main_lines) == 1
    assert "main label" in main_lines[0]
    sub_lines = [l for l in lines if not l.startswith("*")]
    assert "sub" in sub_lines[0]


def test_sessions_branch_override(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    import subprocess
    subprocess.run(["git", "checkout", "main"], cwd=scratch_repo,
                   check=True, capture_output=True)
    result = run_sms(["sessions", "--branch", "feature-x"], cwd=scratch_repo)
    assert result.returncode == 0
    assert "*" in result.stdout  # main session is marked
