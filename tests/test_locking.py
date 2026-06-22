"""Concurrent invocations must not corrupt tree.json."""
from __future__ import annotations

import json
import multiprocessing
import os
import subprocess
import sys
from pathlib import Path

from .conftest import SMS


def _add_branch(repo: str, name: str, home: str) -> int:
    env = os.environ.copy()
    env["HOME"] = home
    return subprocess.run(
        [sys.executable, str(SMS), "debug-tree", "add-branch", name, "main"],
        cwd=repo, env=env, capture_output=True,
    ).returncode


def test_concurrent_add_branch(scratch_repo: Path, isolated_home: Path) -> None:
    """20 parallel add-branch calls all succeed and tree.json contains all 20."""
    repo = str(scratch_repo)
    home = str(isolated_home)
    names = [f"b{i:02d}" for i in range(20)]

    with multiprocessing.Pool(processes=8) as pool:
        results = pool.starmap(_add_branch, [(repo, n, home) for n in names])

    assert all(rc == 0 for rc in results), f"failures: {results}"
    tree = json.loads((scratch_repo / ".git" / "sms" / "tree.json").read_text())
    assert set(tree["branches"]) == set(names)
