from pathlib import Path

from .conftest import run_sms


def test_sms_runs(scratch_repo: Path, isolated_home: Path) -> None:
    """sms with no args exits non-zero (placeholder behavior for now)."""
    result = run_sms([], cwd=scratch_repo)
    assert result.returncode == 2
