"""Tests for `sms session-delete`."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .conftest import run_sms


def _read_tree(repo: Path) -> dict:
    return json.loads((repo / ".git" / "sms" / "tree.json").read_text())


def _projects(home: Path, cwd: Path) -> Path:
    return home / ".claude" / "projects" / str(cwd.resolve()).replace("/", "-")


def test_session_delete_removes_tree_entry_and_symlink(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    # Symlink exists; canonical may be a dangling file path (no content yet)
    link = _projects(isolated_home, scratch_repo) / f"{uuid}.jsonl"
    assert link.is_symlink()

    # Materialize the canonical so delete has something to remove besides symlink
    canonical = scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{uuid}.jsonl"
    canonical.write_text('{"line":1}\n')

    result = run_sms(["session-delete", uuid], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr

    # Symlink, canonical, and tree entry all gone
    assert not link.exists() and not link.is_symlink()
    assert not canonical.exists()
    t = _read_tree(scratch_repo)
    assert uuid not in t["branches"]["feature-x"]["sessions"]


def test_session_delete_accepts_uuid_prefix(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    result = run_sms(["session-delete", uuid[:8]], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr


def test_session_delete_errors_on_unknown_uuid(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    result = run_sms(["session-delete", "ffffffff-ffff-ffff-ffff-ffffffffffff"], cwd=scratch_repo)
    assert result.returncode != 0
    assert "no session" in result.stderr.lower() or "no match" in result.stderr.lower()


def test_session_delete_refuses_current_session(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """Refuse to delete the currently-running session (would corrupt live jsonl)."""
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    result = run_sms(
        ["session-delete", uuid],
        cwd=scratch_repo,
        env_extra={"CLAUDE_CODE_SESSION_ID": uuid},
    )
    assert result.returncode != 0
    assert "refusing" in result.stderr.lower() or "current" in result.stderr.lower()


def test_session_delete_removes_file_history_and_session_env(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    uuid = next(iter(t["branches"]["feature-x"]["sessions"]))

    # Simulate the per-uuid caches outside projects/
    fh = isolated_home / ".claude" / "file-history" / uuid
    se = isolated_home / ".claude" / "session-env" / uuid
    fh.mkdir(parents=True); (fh / "snap.txt").write_text("payload\n")
    se.mkdir(parents=True); (se / "env.json").write_text("{}")

    run_sms(["session-delete", uuid], cwd=scratch_repo)
    assert not fh.exists()
    assert not se.exists()
