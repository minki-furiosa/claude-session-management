"""Tests for `sms set-main`."""
from __future__ import annotations

import json
from pathlib import Path

from .conftest import run_sms


def test_set_main_flips_flags(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    t = json.loads((scratch_repo / ".git" / "sms" / "tree.json").read_text())
    parent = next(iter(t["branches"]["feature-x"]["sessions"]))
    (scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{parent}.jsonl").write_text("{}\n")
    result = run_sms(["fork", "--from", parent, "--no-launch"], cwd=scratch_repo)
    new_uuid = result.stdout.strip().splitlines()[-1]

    assert run_sms(["set-main", new_uuid], cwd=scratch_repo).returncode == 0

    t = json.loads((scratch_repo / ".git" / "sms" / "tree.json").read_text())
    sessions = t["branches"]["feature-x"]["sessions"]
    assert sessions[new_uuid]["is_main"] is True
    assert sessions[parent]["is_main"] is False


def test_set_main_prefix(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    t = json.loads((scratch_repo / ".git" / "sms" / "tree.json").read_text())
    uuid = next(iter(t["branches"]["feature-x"]["sessions"]))
    assert run_sms(["set-main", uuid[:8]], cwd=scratch_repo).returncode == 0
