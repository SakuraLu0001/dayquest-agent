from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_candidate_pack_carries_exact_evidence_and_commands():
    text = (PROJECT_ROOT / "RESUME_EVIDENCE_CANDIDATE.md").read_text(encoding="utf-8")
    assert "10E8D671AD86AF8099820B99E226822799266D0B8F3524377253EDAB94057634" in text
    assert "769FD95B9161108A5145AF14F5679356DE4B7DE25BBECB5CF4237327A19AE351" in text
    assert "python -B scripts/run_product_v2.py --check" in text
    assert "python -B scripts/run_timeline_mvp.py --check" in text
    assert "python -B scripts/run_comparison_benchmark.py --check" in text
    assert "python -B scripts/scan_public_artifacts.py" in text


def test_candidate_pack_does_not_inflate_public_or_hiring_status():
    text = (PROJECT_ROOT / "RESUME_EVIDENCE_CANDIDATE.md").read_text(encoding="utf-8")
    assert "not a final resume bullet" in text
    assert "External CI" in text
    assert "not an internship-readiness score" in text
    assert "independent user demonstration has not yet been recorded" in text
    assert "production reliability, and universal superiority are not claimed" in text


def test_candidate_pack_has_exact_resume_point_and_publication_gates():
    text = (PROJECT_ROOT / "RESUME_EVIDENCE_CANDIDATE.md").read_text(encoding="utf-8")
    assert "## Exact Resume Point" in text
    assert "MIT, the public push" in text
    assert "Actions run 33315185898" in text
    assert "local-only resume bullet draft" in text
    assert "Do not create a Release" in text
