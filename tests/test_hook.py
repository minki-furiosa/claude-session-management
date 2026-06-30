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
    assert "sms branch memory" in out
    assert "sms global memory" in out


def test_hook_global_notes_path_is_repo_level(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """Global memory path is <repo>/.git/sms/notes (not under branches/)."""
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    result = run_sms(["hook", "session-start"], cwd=scratch_repo)
    expected = str(scratch_repo / ".git" / "sms" / "notes")
    assert expected in result.stdout
    # Branch memory is a sibling under branches/, not the global one.
    assert str(scratch_repo / ".git" / "sms" / "branches" / "feature-x" / "notes") in result.stdout


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


def test_hook_identifies_forked_session(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """With --session-id of a fork, the hook tells it that it's a forked sub
    and the history above belongs to the parent."""
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = json.loads((scratch_repo / ".git" / "sms" / "tree.json").read_text())
    parent = next(iter(t["branches"]["feature-x"]["sessions"]))
    (scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{parent}.jsonl").write_text("{}\n")
    r = run_sms(["fork", "--from", parent, "--name", "reviewer", "--no-launch"], cwd=scratch_repo)
    fork_uuid = r.stdout.strip().splitlines()[-1]

    out = run_sms(["hook", "session-start", "--session-id", fork_uuid], cwd=scratch_repo).stdout
    assert "session role" in out.lower()
    assert "FORKED" in out
    assert "reviewer" in out
    assert fork_uuid in out                 # the fork's own id is stated
    assert parent in out                    # forked-from parent is named
    assert "inherited from the parent" in out
    # No blanket "don't fork" rule (it wrongly blocked an explicit /sms-fork).
    assert "do not create or fork sessions" not in out.lower()


def test_hook_identifies_main_session(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    t = json.loads((scratch_repo / ".git" / "sms" / "tree.json").read_text())
    main = next(iter(t["branches"]["feature-x"]["sessions"]))
    out = run_sms(["hook", "session-start", "--session-id", main], cwd=scratch_repo).stdout
    assert "MAIN session" in out
    assert main in out  # main session's own id is stated too


def test_hook_no_role_without_session_id(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """Without --session-id, the role block is omitted (back-compat)."""
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    out = run_sms(["hook", "session-start"], cwd=scratch_repo).stdout
    assert "session role" not in out.lower()
    assert "sms context" in out.lower()  # branch context still emitted
