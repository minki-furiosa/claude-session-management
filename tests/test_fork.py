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
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
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
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
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
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    parent_uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    canonical = scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{parent_uuid}.jsonl"
    canonical.write_text('{"line":1}\n')

    result = run_sms(
        ["fork", "--name", "from-env"],
        cwd=scratch_repo,
        env_extra={"CLAUDE_CODE_SESSION_ID": parent_uuid},
    )
    assert result.returncode == 0, result.stderr
    new_uuid = result.stdout.strip().splitlines()[-1]
    t = _read_tree(scratch_repo)
    assert new_uuid in t["branches"]["feature-x"]["sessions"]


def test_fork_copies_subdir_if_present(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
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


def test_fork_default_name_numbered(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """Without --name, forks are numbered relative to existing sessions on the branch."""
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    parent_uuid = next(iter(t["branches"]["feature-x"]["sessions"]))
    canonical = scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{parent_uuid}.jsonl"
    canonical.write_text("{}\n")

    r1 = run_sms(["fork", "--from", parent_uuid], cwd=scratch_repo)
    u1 = r1.stdout.strip().splitlines()[-1]
    r2 = run_sms(["fork", "--from", parent_uuid], cwd=scratch_repo)
    u2 = r2.stdout.strip().splitlines()[-1]

    t = _read_tree(scratch_repo)
    sessions = t["branches"]["feature-x"]["sessions"]
    assert sessions[u1]["name"] == "feature-x (2)"
    assert sessions[u2]["name"] == "feature-x (3)"


def test_fork_mirrors_parent_symlinks_when_branch_differs(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """When the current worktree's branch differs from the session's branch,
    fork still drops a symlink in every projects dir that has the parent's
    symlink — keeping the fork visible in the picker the user is using."""
    import subprocess
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    parent_uuid = next(iter(t["branches"]["feature-x"]["sessions"]))
    canonical = scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{parent_uuid}.jsonl"
    canonical.write_text("{}\n")

    # Switch the worktree to a different branch (without symlink cleanup —
    # mirrors the real-life case where the user did plain `git checkout`).
    subprocess.run(["git", "checkout", "main"], cwd=scratch_repo,
                   check=True, capture_output=True)

    # Confirm parent symlink is still in projects dir (left over from sms new).
    cwd_hash = str(scratch_repo.resolve()).replace("/", "-")
    pd = isolated_home / ".claude" / "projects" / cwd_hash
    assert (pd / f"{parent_uuid}.jsonl").is_symlink()

    # Fork. The worktree is now on `main`, not `feature-x`, but the fork's
    # symlink should still appear in this projects dir (mirroring parent).
    result = run_sms(["fork", "--from", parent_uuid], cwd=scratch_repo)
    new_uuid = result.stdout.strip().splitlines()[-1]
    assert (pd / f"{new_uuid}.jsonl").is_symlink()


def test_fork_errors_without_parent_uuid_source(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """No --from and no CLAUDE_CODE_SESSION_ID env → error."""
    result = run_sms(["fork", "--name", "x"], cwd=scratch_repo)
    assert result.returncode != 0
    assert "CLAUDE_CODE_SESSION_ID" in result.stderr or "--from" in result.stderr
