from pathlib import Path

from scripts.scan_public_artifacts import scan


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_committed_public_artifacts_pass_scoped_scan():
    assert scan(PROJECT_ROOT) == []


def test_scan_does_not_read_ignored_env_files(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("DO_NOT_READ=secret", encoding="utf-8")
    (tmp_path / "artifacts").mkdir()
    monkeypatch.setattr("scripts.scan_public_artifacts.tracked_paths", lambda _: [])
    assert scan(tmp_path) == []


def test_scan_flags_public_artifact_absolute_path(tmp_path, monkeypatch):
    artifact = tmp_path / "artifacts" / "bad.json"
    artifact.parent.mkdir()
    artifact.write_text('{"path": "C:\\\\private\\\\file"}', encoding="utf-8")
    monkeypatch.setattr("scripts.scan_public_artifacts.tracked_paths", lambda _: [])
    assert scan(tmp_path) == ["absolute_windows_path:artifacts/bad.json"]
