import struct
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = PROJECT_ROOT / "docs" / "assets"
BASELINE_COMMIT = "a1322b21f412bbe72376d575ac84053a7b54982b"
BASELINE_RUN = "33315509118"
SURFACE_COMMIT = "da8dfa8241ba2693c54a469c7484cbc4ad90740d"
SURFACE_RUN = "33317902718"


def test_readme_is_product_first_and_keeps_legacy_subordinate():
    text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    expected_order = (
        "**An evidence-first MCP timeline debugger",
        "docs/assets/dayquest-product-v2-replay.jpg",
        "## Three-step no-key quickstart",
        "## Product V2 · reversible evidence replay",
        "## Architecture",
        "## Verifiable results",
        "## Mature-project comparison boundary",
        "## Limitations",
        "## Legacy / Original Hackathon Prototype",
    )
    positions = [text.index(marker) for marker in expected_order]
    assert positions == sorted(positions)
    assert "docs/assets/dayquest-architecture.svg" in text
    assert "No GitHub Release has been created" in text


def _jpeg_dimensions(content: bytes) -> tuple[int, int]:
    offset = 2
    start_of_frame = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while offset + 8 < len(content):
        if content[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(content) and content[offset] == 0xFF:
            offset += 1
        marker = content[offset]
        offset += 1
        if marker in start_of_frame:
            height, width = struct.unpack(">HH", content[offset + 3 : offset + 7])
            return width, height
        if marker in {0xD8, 0xD9}:
            continue
        segment_length = int.from_bytes(content[offset : offset + 2], "big")
        offset += segment_length
    raise AssertionError("JPEG dimensions not found")


def test_real_product_capture_is_a_bounded_jpeg():
    content = (ASSET_ROOT / "dayquest-product-v2-replay.jpg").read_bytes()
    assert content.startswith(b"\xff\xd8\xff")
    assert content.endswith(b"\xff\xd9")
    width, height = _jpeg_dimensions(content)
    assert (width, height) == (1280, 720)
    assert len(content) > 50_000


def test_architecture_svg_is_accessible_and_matches_implemented_path():
    path = ASSET_ROOT / "dayquest-architecture.svg"
    root = ET.parse(path).getroot()
    assert root.attrib["width"] == "1280"
    assert root.attrib["height"] == "608"
    text = path.read_text(encoding="utf-8")
    for marker in (
        "Read-only localhost MCP",
        "Claim + policy evaluation",
        "Supported",
        "Unknown",
        "Conflict",
        "Canonical intervention receipts",
        "12-case reports + aggregate",
        "200 pytest checks",
    ):
        assert marker in text
    assert "not production reliability" in text


def test_public_evidence_documents_bind_the_verified_technical_baseline():
    for name in (
        "README.md",
        "PUBLICATION_PREFLIGHT.md",
        "PUBLIC_EVIDENCE_RECEIPT.md",
        "RESUME_EVIDENCE_CANDIDATE.md",
    ):
        text = (PROJECT_ROOT / name).read_text(encoding="utf-8")
        assert BASELINE_COMMIT in text
        assert BASELINE_RUN in text
        assert SURFACE_COMMIT in text
        assert SURFACE_RUN in text
    receipt = (PROJECT_ROOT / "PUBLIC_EVIDENCE_RECEIPT.md").read_text(encoding="utf-8")
    assert "Recruiter Surface Published / External CI Green" in receipt
