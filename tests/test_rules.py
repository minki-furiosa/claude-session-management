"""Tests for `sms rules` + rule injection in the hook."""
from __future__ import annotations

from pathlib import Path

from .conftest import run_sms


def test_rules_creates_default_and_prints_path(scratch_repo: Path, isolated_home: Path) -> None:
    r = run_sms(["rules"], cwd=scratch_repo)
    assert r.returncode == 0, r.stderr
    path = scratch_repo / ".git" / "sms" / "rules.md"
    assert path.exists()
    assert r.stdout.strip() == str(path)
    assert "Stay on the branch you were given" in path.read_text()


def test_rules_show_prints_content(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["rules"], cwd=scratch_repo)  # create
    r = run_sms(["rules", "--show"], cwd=scratch_repo)
    assert r.returncode == 0, r.stderr
    assert "Stay on the branch you were given" in r.stdout


def test_rules_preserves_user_edits(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["rules"], cwd=scratch_repo)
    path = scratch_repo / ".git" / "sms" / "rules.md"
    path.write_text("- my own rule\n")
    # second call must not overwrite
    r = run_sms(["rules"], cwd=scratch_repo)
    assert r.returncode == 0
    assert path.read_text() == "- my own rule\n"


def test_hook_injects_rules(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    rules = scratch_repo / ".git" / "sms" / "rules.md"
    rules.parent.mkdir(parents=True, exist_ok=True)
    rules.write_text("- always write tests first\n")
    out = run_sms(["hook", "session-start"], cwd=scratch_repo).stdout
    assert "=== sms rules ===" in out
    assert "always write tests first" in out


def test_hook_no_rules_section_when_file_absent(scratch_repo: Path, isolated_home: Path) -> None:
    run_sms(["new", "feature-x", "--no-launch", "--no-materialize"], cwd=scratch_repo)
    out = run_sms(["hook", "session-start"], cwd=scratch_repo).stdout
    assert "=== sms rules ===" not in out
