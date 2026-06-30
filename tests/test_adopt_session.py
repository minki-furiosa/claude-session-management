"""Tests for `sms adopt-session` (bring an existing non-sms session under sms)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .conftest import run_sms


def _read_tree(repo: Path) -> dict:
    return json.loads((repo / ".git" / "sms" / "tree.json").read_text())


def _projects(home: Path, cwd: Path) -> Path:
    return home / ".claude" / "projects" / str(cwd.resolve()).replace("/", "-")


def _seed_existing_session(home: Path, repo: Path, uuid: str, branch: str = "main") -> Path:
    """Write a plain (non-sms) session jsonl into the projects dir, as Claude
    would for a session used without sms."""
    pd = _projects(home, repo)
    pd.mkdir(parents=True, exist_ok=True)
    f = pd / f"{uuid}.jsonl"
    f.write_text(
        json.dumps({"type": "user", "uuid": "m1", "parentUuid": None,
                    "message": {"role": "user", "content": "real work"},
                    "sessionId": uuid, "gitBranch": branch}) + "\n"
    )
    return f


def test_adopt_session_relocates_symlinks_and_registers(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    uuid = "12345678-1111-2222-3333-444444444444"
    src = _seed_existing_session(isolated_home, scratch_repo, uuid, "main")
    original = src.read_text()

    result = run_sms(["adopt-session", uuid], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr

    # canonical now holds the file; projects entry is a symlink to it
    canonical = scratch_repo / ".git" / "sms" / "sessions" / "main" / f"{uuid}.jsonl"
    assert canonical.exists()
    assert canonical.read_text() == original          # content untouched
    assert src.is_symlink()
    assert os.readlink(src) == str(canonical)

    # branch + session registered; first session is main
    t = _read_tree(scratch_repo)
    assert "main" in t["branches"]
    s = t["branches"]["main"]["sessions"][uuid]
    assert s["is_main"] is True


def test_adopt_session_does_not_rewrite_transcript(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """Adoption must NOT alter the session's own content (it's a real session,
    not a fork copy) — sessionId stays as-is."""
    uuid = "12345678-1111-2222-3333-444444444444"
    _seed_existing_session(isolated_home, scratch_repo, uuid, "main")
    run_sms(["adopt-session", uuid], cwd=scratch_repo)
    canonical = scratch_repo / ".git" / "sms" / "sessions" / "main" / f"{uuid}.jsonl"
    first = json.loads(canonical.read_text().splitlines()[0])
    assert first["sessionId"] == uuid           # unchanged
    assert first["message"]["content"] == "real work"


def test_adopt_session_with_name_appends_title(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    uuid = "12345678-1111-2222-3333-444444444444"
    _seed_existing_session(isolated_home, scratch_repo, uuid, "main")
    run_sms(["adopt-session", uuid, "--name", "rescued chat"], cwd=scratch_repo)
    canonical = scratch_repo / ".git" / "sms" / "sessions" / "main" / f"{uuid}.jsonl"
    text = canonical.read_text()
    assert '"customTitle": "rescued chat"' in text
    t = _read_tree(scratch_repo)
    assert t["branches"]["main"]["sessions"][uuid]["name"] == "rescued chat"


def test_adopt_session_second_is_sub(scratch_repo: Path, isolated_home: Path) -> None:
    u1 = "11111111-1111-1111-1111-111111111111"
    u2 = "22222222-2222-2222-2222-222222222222"
    _seed_existing_session(isolated_home, scratch_repo, u1, "main")
    run_sms(["adopt-session", u1], cwd=scratch_repo)
    _seed_existing_session(isolated_home, scratch_repo, u2, "main")
    run_sms(["adopt-session", u2], cwd=scratch_repo)
    t = _read_tree(scratch_repo)
    sessions = t["branches"]["main"]["sessions"]
    assert sessions[u1]["is_main"] is True
    assert sessions[u2]["is_main"] is False


def test_adopt_session_errors_if_file_absent(scratch_repo: Path, isolated_home: Path) -> None:
    result = run_sms(["adopt-session", "deadbeef-0000-0000-0000-000000000000"], cwd=scratch_repo)
    assert result.returncode != 0
    assert "no session file" in result.stderr.lower()


def test_adopt_session_errors_if_already_symlink(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    uuid = "12345678-1111-2222-3333-444444444444"
    _seed_existing_session(isolated_home, scratch_repo, uuid, "main")
    run_sms(["adopt-session", uuid], cwd=scratch_repo)        # now a symlink
    result = run_sms(["adopt-session", uuid], cwd=scratch_repo)
    assert result.returncode != 0
    assert "symlink" in result.stderr.lower() or "already" in result.stderr.lower()


def test_adopt_session_preserves_inode_for_live_session(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """The relocate is a rename (same fs), so the inode is preserved — a live
    session writing through an open fd keeps the same file."""
    uuid = "12345678-1111-2222-3333-444444444444"
    src = _seed_existing_session(isolated_home, scratch_repo, uuid, "main")
    before = src.stat().st_ino
    run_sms(["adopt-session", uuid], cwd=scratch_repo)
    canonical = scratch_repo / ".git" / "sms" / "sessions" / "main" / f"{uuid}.jsonl"
    assert canonical.stat().st_ino == before
