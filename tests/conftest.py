"""Pytest fixtures: isolated $HOME and a scratch git repo per test."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

SMS = Path(__file__).resolve().parent.parent / "sms"


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect $HOME to a temp dir so ~/.claude/* writes are sandboxed."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    (home / ".claude" / "projects").mkdir(parents=True)
    return home


@pytest.fixture
def scratch_repo(tmp_path: Path) -> Path:
    """Create a fresh git repo (main branch) with one commit, cd into it."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "sms-test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "sms test"], cwd=repo, check=True)
    (repo / "README.md").write_text("scratch\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo


def run_sms(args: list[str], cwd: Path, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Invoke the sms CLI in a subprocess and return the result.

    By default, strips CLAUDE_CODE_SESSION_ID / CLAUDE_SESSION_ID from the env
    so that tests don't accidentally inherit the controlling session's UUID.
    Tests that want a specific session UUID pass it explicitly via env_extra.
    """
    env = os.environ.copy()
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("CLAUDE_SESSION_ID", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(SMS), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
