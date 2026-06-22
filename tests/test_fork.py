"""Tests for `sms fork`."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .conftest import run_sms


def _read_tree(repo: Path) -> dict:
    return json.loads((repo / ".git" / "sms" / "tree.json").read_text())


def test_fork_copies_jsonl_and_registers(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    parent_uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    # Write dummy content into the canonical jsonl to verify copy
    canonical = scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{parent_uuid}.jsonl"
    canonical.write_text('{"line":1}\n{"line":2}\n')

    result = run_sms(["fork", "--from", parent_uuid, "--name", "review-perf"],
                     cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    new_uuid = result.stdout.strip().splitlines()[-1]

    # Tree entry
    t = _read_tree(scratch_repo)
    sessions = t["branches"]["feature-x"]["sessions"]
    assert new_uuid in sessions
    assert sessions[new_uuid]["parent_uuid"] == parent_uuid
    assert sessions[new_uuid]["is_main"] is False
    assert sessions[new_uuid]["name"] == "review-perf"

    # Canonical copy
    new_canonical = scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{new_uuid}.jsonl"
    assert new_canonical.read_text() == '{"line":1}\n{"line":2}\n'


def test_fork_creates_symlink_in_current_worktree(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    parent_uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    canonical = scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{parent_uuid}.jsonl"
    canonical.write_text('{"line":1}\n')

    result = run_sms(["fork", "--from", parent_uuid], cwd=scratch_repo)
    new_uuid = result.stdout.strip().splitlines()[-1]

    cwd_hash = str(scratch_repo.resolve()).replace("/", "-")
    link = isolated_home / ".claude" / "projects" / cwd_hash / f"{new_uuid}.jsonl"
    assert link.is_symlink()
    assert os.readlink(link).endswith(f"{new_uuid}.jsonl")


def test_fork_uses_claude_session_id_env(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    parent_uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    canonical = scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{parent_uuid}.jsonl"
    canonical.write_text('{"line":1}\n')

    result = run_sms(
        ["fork", "--name", "from-env"],
        cwd=scratch_repo,
        env_extra={"CLAUDE_SESSION_ID": parent_uuid},
    )
    assert result.returncode == 0, result.stderr
    new_uuid = result.stdout.strip().splitlines()[-1]
    t = _read_tree(scratch_repo)
    assert new_uuid in t["branches"]["feature-x"]["sessions"]


def test_fork_copies_subdir_if_present(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    parent_uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    sessions_dir = scratch_repo / ".git" / "sms" / "sessions" / "feature-x"
    (sessions_dir / f"{parent_uuid}.jsonl").write_text("{}\n")
    sub = sessions_dir / parent_uuid / "tool-results"
    sub.mkdir(parents=True)
    (sub / "data.txt").write_text("payload\n")

    result = run_sms(["fork", "--from", parent_uuid], cwd=scratch_repo)
    new_uuid = result.stdout.strip().splitlines()[-1]
    new_sub = sessions_dir / new_uuid / "tool-results" / "data.txt"
    assert new_sub.read_text() == "payload\n"


def test_fork_errors_without_parent_uuid_source(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """No --from and no CLAUDE_SESSION_ID env → error."""
    result = run_sms(["fork", "--name", "x"], cwd=scratch_repo)
    assert result.returncode != 0
    assert "CLAUDE_SESSION_ID" in result.stderr or "--from" in result.stderr
