"""Tests for symlink create/remove/scan."""
from __future__ import annotations

import os
from pathlib import Path

from .conftest import run_sms


def _canonical(repo: Path, branch: str, uuid: str) -> Path:
    return repo / ".git" / "sms" / "sessions" / branch / f"{uuid}.jsonl"


def _projects_link(home: Path, cwd: Path, uuid: str) -> Path:
    h = str(cwd.resolve()).replace("/", "-")
    return home / ".claude" / "projects" / h / f"{uuid}.jsonl"


def test_make_symlink_creates_dangling_link(scratch_repo: Path, isolated_home: Path) -> None:
    uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    result = run_sms(
        ["debug-symlink", "make", "feature-x", uuid], cwd=scratch_repo,
    )
    assert result.returncode == 0, result.stderr
    link = _projects_link(isolated_home, scratch_repo, uuid)
    assert link.is_symlink()
    assert os.readlink(link) == str(_canonical(scratch_repo, "feature-x", uuid))


def test_make_symlink_idempotent(scratch_repo: Path, isolated_home: Path) -> None:
    uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    for _ in range(3):
        result = run_sms(
            ["debug-symlink", "make", "feature-x", uuid], cwd=scratch_repo,
        )
        assert result.returncode == 0, result.stderr


def test_make_symlink_backs_up_differing_regular_file(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """A regular file that DIFFERS from canonical is backed up, then replaced
    with the symlink — no data lost, no refusal."""
    uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    # canonical has the real content
    canonical = _canonical(scratch_repo, "feature-x", uuid)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text("canonical real content\n")
    # projects dir has a differing stub
    link = _projects_link(isolated_home, scratch_repo, uuid)
    link.parent.mkdir(parents=True, exist_ok=True)
    link.write_text("stub created by claude\n")

    result = run_sms(["debug-symlink", "make", "feature-x", uuid], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    # link now points at canonical
    assert link.is_symlink()
    assert os.readlink(link) == str(canonical)
    # the differing content was backed up
    pd = link.parent
    backups = list(pd.glob(f"{uuid}.jsonl.conflict-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "stub created by claude\n"
    assert "Backed it up" in result.stderr


def test_make_symlink_replaces_identical_regular_file_without_backup(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """A regular file IDENTICAL to canonical is replaced silently (no backup)."""
    uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    canonical = _canonical(scratch_repo, "feature-x", uuid)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text("same bytes\n")
    link = _projects_link(isolated_home, scratch_repo, uuid)
    link.parent.mkdir(parents=True, exist_ok=True)
    link.write_text("same bytes\n")

    result = run_sms(["debug-symlink", "make", "feature-x", uuid], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    assert link.is_symlink()
    assert os.readlink(link) == str(canonical)
    # no backup created
    assert not list(link.parent.glob(f"{uuid}.jsonl.conflict-*"))


def test_remove_symlink(scratch_repo: Path, isolated_home: Path) -> None:
    uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    run_sms(["debug-symlink", "make", "feature-x", uuid], cwd=scratch_repo)
    result = run_sms(["debug-symlink", "remove", uuid], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    assert not _projects_link(isolated_home, scratch_repo, uuid).exists()


def test_remove_does_not_touch_regular_file(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    link = _projects_link(isolated_home, scratch_repo, uuid)
    link.parent.mkdir(parents=True, exist_ok=True)
    link.write_text("not a symlink\n")
    result = run_sms(["debug-symlink", "remove", uuid], cwd=scratch_repo)
    assert result.returncode == 0
    assert link.exists() and not link.is_symlink()
    assert link.read_text() == "not a symlink\n"


def test_scan_returns_only_sms_symlinks(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    sms_uuid = "11111111-1111-1111-1111-111111111111"
    other_uuid = "22222222-2222-2222-2222-222222222222"
    run_sms(["debug-symlink", "make", "feature-x", sms_uuid], cwd=scratch_repo)
    # Drop a non-sms file in the same projects dir
    plain = _projects_link(isolated_home, scratch_repo, other_uuid)
    plain.parent.mkdir(parents=True, exist_ok=True)
    plain.write_text("not a sms session\n")

    result = run_sms(["debug-symlink", "scan"], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr
    seen = dict(line.split("=", 1) for line in result.stdout.strip().splitlines() if line)
    assert sms_uuid in seen
    assert other_uuid not in seen


def test_fix_visibility_rewrites_sdk_cli_entrypoint(
    scratch_repo: Path, isolated_home: Path,
) -> None:
    """sdk-cli entrypoint markers (which hide a session from the picker) are
    rewritten to the interactive entrypoint, through the projects-dir symlink."""
    import os as _os
    uuid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    canonical = _canonical(scratch_repo, "feature-x", uuid)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(
        '{"type":"queue-operation","sessionId":"%s"}\n'
        '{"a":1,"entrypoint":"sdk-cli","sessionId":"%s"}\n'
        '{"b":2,"entrypoint":"sdk-cli","sessionId":"%s"}\n' % (uuid, uuid, uuid)
    )
    # link it into the projects dir (as `sms` would)
    run_sms(["debug-symlink", "make", "feature-x", uuid], cwd=scratch_repo)
    link = _projects_link(isolated_home, scratch_repo, uuid)
    assert link.is_symlink()

    result = run_sms(["debug-symlink", "fix-visibility", uuid], cwd=scratch_repo)
    assert result.returncode == 0, result.stderr

    # canonical (followed through the symlink) no longer has sdk-cli
    text = canonical.read_text()
    assert "sdk-cli" not in text
    assert text.count('"entrypoint":"claude-vscode"') == 2
    # the symlink is intact (inode preserved — write followed the link)
    assert link.is_symlink()
