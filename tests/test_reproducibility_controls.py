from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _lock_requirements():
    lines = (PROJECT_ROOT / "requirements.lock.txt").read_text(encoding="utf-8").splitlines()
    return [Requirement(line) for line in lines if line and not line.startswith("#")]


def test_lock_is_exact_unique_and_matches_verified_environment():
    requirements = _lock_requirements()
    normalized = [requirement.name.lower().replace("_", "-") for requirement in requirements]
    assert len(normalized) == len(set(normalized))
    for requirement in requirements:
        assert str(requirement.specifier).startswith("==")
        if requirement.marker and not requirement.marker.evaluate():
            continue
        assert metadata.version(requirement.name) in requirement.specifier


def test_ci_uses_lock_and_all_local_evidence_checks():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "requirements.lock.txt" in workflow
    for command in (
        "pytest",
        "generate_synthetic_trace.py --check",
        "run_evaluation_slice.py --check",
        "run_branch_breadth_slice.py --check",
        "run_timeline_slice.py --check",
        "run_timeline_mvp.py --check",
        "run_comparison_benchmark.py --check",
        "scan_public_artifacts.py",
    ):
        assert command in workflow


def test_license_is_accepted_mit_and_security_scope_is_bounded():
    license_decision = (PROJECT_ROOT / "LICENSE_DECISION.md").read_text(encoding="utf-8")
    license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
    security = (PROJECT_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "Accepted / MIT License Authorized" in license_decision
    assert "The root `LICENSE` file is the operative license grant" in license_decision
    assert license_text.startswith("MIT License\n\nCopyright (c) 2026 Liyang Luo")
    assert "not general secret scanning" in security
    assert "does not read ignored `.env`" in security
