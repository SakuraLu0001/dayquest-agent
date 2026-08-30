from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_candidate_pack_carries_exact_evidence_and_commands():
    text = (PROJECT_ROOT / "RESUME_EVIDENCE_CANDIDATE.md").read_text(encoding="utf-8")
    assert "10E8D671AD86AF8099820B99E226822799266D0B8F3524377253EDAB94057634" in text
    assert "769FD95B9161108A5145AF14F5679356DE4B7DE25BBECB5CF4237327A19AE351" in text
    assert "python -B scripts/run_timeline_mvp.py --check" in text
    assert "python -B scripts/run_comparison_benchmark.py --check" in text
    assert "python -B scripts/scan_public_artifacts.py" in text


def test_candidate_pack_does_not_inflate_public_or_hiring_status():
    text = (PROJECT_ROOT / "RESUME_EVIDENCE_CANDIDATE.md").read_text(encoding="utf-8")
    assert "Awaiting User Review" in text
    assert "not a final resume bullet" in text
    assert "GitHub Actions not externally executed" in text
    assert "not a governance fact or internship-readiness score" in text
    assert "independent user demonstration has not yet been recorded" in text


def test_candidate_pack_has_exact_resume_point_and_publication_gates():
    text = (PROJECT_ROOT / "RESUME_EVIDENCE_CANDIDATE.md").read_text(encoding="utf-8")
    assert "## Exact Resume Point" in text
    assert "do not write the final resume bullet, add LICENSE, push, release" in text
    assert "User chooses MIT, Apache-2.0, or no publication" in text
