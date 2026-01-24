from pathlib import Path

from tools.adr.adr_enforcer import ADREnforcementValidator


def test_adr_enforcer_runs_on_repo_root() -> None:
    validator = ADREnforcementValidator(repo_root=Path.cwd())
    report = validator.scan_repo()
    assert report.files_scanned >= 0
    assert report.total_violations >= 0
