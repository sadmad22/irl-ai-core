from __future__ import annotations

from agents.research.claim_evidence_grounding import ground_claims_by_section


def record(evidence_id: str, data: str) -> dict:
    return {
        "evidence_id": evidence_id,
        "domain": "insurance",
        "claim": {"type": "coverage", "attribute": "professional liability"},
        "value": {"type": "description", "data": data},
        "subject": {"type": "audience", "id": "consultants"},
        "source": {"artifact": "research"},
    }


def unrelated_record(evidence_id: str) -> dict:
    return {
        "evidence_id": evidence_id,
        "domain": "accounting",
        "claim": {"type": "software", "attribute": "bookkeeping automation"},
        "value": {
            "type": "description",
            "data": "Tax filing automation for small accounting firms.",
        },
        "subject": {"type": "audience", "id": "accountants"},
        "source": {"artifact": "research"},
    }


def editorial(
    evidence_id: str,
    section_index: int,
    text: str,
    status: str = "ready",
) -> dict:
    return {
        "evidence_id": evidence_id,
        "section_index": section_index,
        "status": status,
        "text": text,
    }


def test_page_reviewed_editorial_evidence_preserves_canonical_research_id() -> None:
    result = ground_claims_by_section(
        sections=[{
            "evidence_refs": ["ev_1"],
            "body": "International health insurance provides coverage across multiple countries.",
        }],
        evidence_records=[
            record("ev_1", "international health insurance coverage")
        ],
        editorial_evidence=[
            editorial(
                "ev_1",
                1,
                "International health insurance provides coverage across multiple countries.",
            )
        ],
    )

    assert result[0][0]["grounding_status"] == "grounded"
    assert result[0][0]["evidence_refs"] == ["ev_1"]


def test_snippet_only_editorial_evidence_is_ignored_when_research_evidence_can_ground() -> None:
    sections = [{
        "evidence_refs": ["ev_1"],
        "body": "International health insurance provides coverage across multiple countries.",
    }]
    evidence_records = [
        record("ev_1", "international health insurance coverage")
    ]

    without_editorial = ground_claims_by_section(
        sections=sections,
        evidence_records=evidence_records,
    )
    with_candidate_editorial = ground_claims_by_section(
        sections=sections,
        evidence_records=evidence_records,
        editorial_evidence=[
            editorial(
                "ev_1",
                1,
                "International health insurance provides coverage across multiple countries.",
                status="candidate",
            )
        ],
    )

    assert with_candidate_editorial == without_editorial
    assert with_candidate_editorial[0][0]["grounding_status"] == "grounded"
    assert with_candidate_editorial[0][0]["evidence_refs"] == ["ev_1"]


def test_snippet_only_editorial_evidence_cannot_ground_when_research_evidence_cannot() -> None:
    result = ground_claims_by_section(
        sections=[{
            "evidence_refs": ["ev_1"],
            "body": "International health insurance provides coverage across multiple countries.",
        }],
        evidence_records=[
            unrelated_record("ev_1")
        ],
        editorial_evidence=[
            editorial(
                "ev_1",
                1,
                "International health insurance provides coverage across multiple countries.",
                status="candidate",
            )
        ],
    )

    assert result[0][0]["grounding_status"] == "blocked"
    assert result[0][0]["evidence_refs"] == []


def test_unmatched_editorial_text_falls_back_to_research_evidence() -> None:
    result = ground_claims_by_section(
        sections=[{
            "evidence_refs": ["ev_1"],
            "body": "Consultants face professional liability risks.",
        }],
        evidence_records=[
            record("ev_1", "consultants professional liability risks professional services")
        ],
        editorial_evidence=[
            editorial("ev_1", 1, "This unrelated source text discusses travel insurance.")
        ],
    )

    assert result[0][0]["grounding_status"] == "grounded"
    assert result[0][0]["evidence_refs"] == ["ev_1"]


def test_editorial_evidence_is_section_scoped() -> None:
    result = ground_claims_by_section(
        sections=[
            {
                "evidence_refs": ["ev_1"],
                "body": "Professional liability coverage protects consultants.",
            },
            {
                "evidence_refs": ["ev_1"],
                "body": "Professional liability coverage protects consultants.",
            },
        ],
        evidence_records=[
            record("ev_1", "consultants professional liability coverage")
        ],
        editorial_evidence=[
            editorial(
                "ev_1",
                2,
                "Professional liability coverage protects consultants.",
            )
        ],
    )

    assert result[0][0]["grounding_status"] == "grounded"
    assert result[0][0]["evidence_refs"] == ["ev_1"]
    assert result[1][0]["grounding_status"] == "grounded"
    assert result[1][0]["evidence_refs"] == ["ev_1"]


def test_editorial_source_from_wrong_section_cannot_ground_claim() -> None:
    result = ground_claims_by_section(
        sections=[{
            "evidence_refs": ["ev_1"],
            "body": "The source page states that visitors receive unrelated benefits.",
        }],
        evidence_records=[
            record("ev_1", "unrelated accounting software information")
        ],
        editorial_evidence=[
            editorial(
                "ev_1",
                2,
                "The source page states that consultants receive unrelated coverage.",
            )
        ],
    )

    assert result[0][0]["grounding_status"] == "blocked"
    assert result[0][0]["evidence_refs"] == []
