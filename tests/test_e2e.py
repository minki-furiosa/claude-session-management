"""End-to-end test of the sms lifecycle against real claude.

Requires `claude` on PATH and a valid auth session. Skipped unless SMS_RUN_E2E=1.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from .conftest import SMS

pytestmark = pytest.mark.skipif(
    os.environ.get("SMS_RUN_E2E") != "1",
    reason="set SMS_RUN_E2E=1 to run e2e",
)


def test_lifecycle_new_fork_checkout_resume(
    scratch_repo: Path, isolated_home: Path, tmp_path: Path,
) -> None:
    """
    1. sms new feature-x → session created, jsonl written through symlink to canonical.
    2. sms fork → second session exists at canonical with copy of first's content.
    3. switch to a fresh worktree on feature-x via sms checkout → symlinks repopulated.
    4. claude --resume on the forked uuid from the second worktree succeeds and writes
       to the canonical file.
    """
    env = os.environ.copy()
    env["HOME"] = str(isolated_home)

    # Step 1: sms new (one-shot prompt via claude --print after we install --session-id manually)
    # Use --no-launch then manually spawn `claude --session-id` with --print, so the test exits.
    r = subprocess.run(
        [sys.executable, str(SMS), "new", "feature-x", "--name", "main session", "--no-launch"],
        cwd=scratch_repo, env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    tree = json.loads((scratch_repo / ".git" / "sms" / "tree.json").read_text())
    main_uuid = next(iter(tree["branches"]["feature-x"]["sessions"]))

    # Use claude --session-id to actually populate the jsonl via the symlink
    r = subprocess.run(
        ["claude", "--session-id", main_uuid, "--print", "Reply OK_NEW_E2E"],
        cwd=scratch_repo, env=env, capture_output=True, text=True, timeout=120,
    )
    assert "OK_NEW_E2E" in r.stdout, r.stderr
    canonical = scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{main_uuid}.jsonl"
    assert canonical.exists() and canonical.stat().st_size > 0

    # Step 2: fork
    r = subprocess.run(
        [sys.executable, str(SMS), "fork", "--from", main_uuid, "--name", "review"],
        cwd=scratch_repo, env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    fork_uuid = r.stdout.strip().splitlines()[-1]
    fork_canonical = scratch_repo / ".git" / "sms" / "sessions" / "feature-x" / f"{fork_uuid}.jsonl"
    assert fork_canonical.exists() and fork_canonical.stat().st_size > 0

    # Step 3: a second worktree on feature-x — first move feature-x away
    subprocess.run(["git", "checkout", "main"], cwd=scratch_repo,
                   check=True, capture_output=True)
    wt = tmp_path / "wtB"
    subprocess.run(["git", "worktree", "add", str(wt), "feature-x"],
                   cwd=scratch_repo, check=True, capture_output=True)
    # Sync from the new worktree
    r = subprocess.run([sys.executable, str(SMS), "sync"], cwd=wt, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    cwd_hash_b = str(wt.resolve()).replace("/", "-")
    link = isolated_home / ".claude" / "projects" / cwd_hash_b / f"{fork_uuid}.jsonl"
    assert link.is_symlink()

    # Step 4: resume the fork from the new worktree
    before_size = fork_canonical.stat().st_size
    r = subprocess.run(
        ["claude", "--resume", fork_uuid, "--print", "Reply OK_RESUMED_E2E"],
        cwd=wt, env=env, capture_output=True, text=True, timeout=120,
    )
    assert "OK_RESUMED_E2E" in r.stdout, r.stderr
    # Canonical grew, confirming writes followed the symlink
    assert fork_canonical.stat().st_size > before_size
