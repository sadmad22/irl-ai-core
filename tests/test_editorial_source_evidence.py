from __future__ import annotations

from agents.research.editorial_source_evidence import build_editorial_evidence


def evidence(evidence_id: str) -> dict:
    return {"evidence_id": evidence_id}


def test_page_reviewed_source_becomes_ready_editorial_evidence() -> None:
    result = build_editorial_evidence(
        evidence_records=[evidence("ev_1")],
        source_pages={
            "ev_1": {
                "section_index": 2,
                "url": "https://example.com/guide",
                "title": "Expat Health Insurance Guide",
                "domain": "example.com",
                "text": "International health insurance can provide coverage across multiple countries.",
                "verification": "page_reviewed",
            }
        },
    )

    assert result == [
        {
            "evidence_id": "ev_1",
            "section_index": 2,
            "status": "ready",
            "text": "International health insurance can provide coverage across multiple countries.",
            "source": {
                "type": "serp_result",
                "url": "https://example.com/guide",
                "title": "Expat Health Insurance Guide",
                "domain": "example.com",
            },
            "provenance": {
                "artifact": "serp-analysis.json",
                "method": "serp-page-editorial-v1",
                "verification": "page_reviewed",
            },
        }
    ]


def test_snippet_only_source_remains_candidate() -> None:
    result = build_editorial_evidence(
        evidence_records=[evidence("ev_1")],
        source_pages={
            "ev_1": {
                "section_index": 1,
                "url": "https://example.com",
                "title": "Example",
                "domain": "example.com",
                "text": "Snippet material.",
                "verification": "snippet_only",
            }
        },
    )

    assert result[0]["status"] == "candidate"
    assert result[0]["provenance"]["method"] == "serp-snippet-editorial-v1"


def test_missing_page_material_is_fail_closed() -> None:
    result = build_editorial_evidence(
        evidence_records=[evidence("ev_1")],
        source_pages={},
    )
    assert result == []


def test_output_is_deterministic() -> None:
    kwargs = {
        "evidence_records": [evidence("ev_2"), evidence("ev_1")],
        "source_pages": {
            "ev_1": {
                "section_index": 1,
                "url": "https://example.com/a",
                "title": "A",
                "domain": "example.com",
                "text": "First source material.",
                "verification": "page_reviewed",
            },
            "ev_2": {
                "section_index": 2,
                "url": "https://example.org/b",
                "title": "B",
                "domain": "example.org",
                "text": "Second source material.",
                "verification": "page_reviewed",
            },
        },
    }

    assert build_editorial_evidence(**kwargs) == build_editorial_evidence(**kwargs)


def test_invalid_section_index_fails_closed() -> None:
    import pytest

    with pytest.raises(ValueError, match="section_index"):
        build_editorial_evidence(
            evidence_records=[evidence("ev_1")],
            source_pages={
                "ev_1": {
                    "section_index": 0,
                    "url": "https://example.com",
                    "title": "Example",
                    "domain": "example.com",
                    "text": "Source material.",
                    "verification": "page_reviewed",
                }
            },
        )

    with pytest.raises(ValueError, match="section_index"):
        build_editorial_evidence(
            evidence_records=[evidence("ev_1")],
            source_pages={
                "ev_1": {
                    "url": "https://example.com",
                    "title": "Example",
                    "domain": "example.com",
                    "text": "Source material.",
                    "verification": "page_reviewed",
                }
            },
        )
