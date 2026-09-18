from __future__ import annotations

import copy

import pytest

from agents.intelligence.input_contract import validate_intelligence_input


REPORT_ID = "rr_001"


def evidence(evidence_id: str = "ev_001", *, report_id: str = REPORT_ID, status: str = "active") -> dict:
    return {
        "evidence_id": evidence_id,
        "report_id": report_id,
        "schema_version": "1.0",
        "type": "observation",
        "domain": "intent",
        "subject": {"type": "keyword", "id": "consultant insurance"},
        "claim": {"type": "query_intent", "attribute": "primary_intent"},
        "value": {"type": "categorical", "data": "commercial"},
        "source": {
            "type": "query",
            "source_id": "consultant insurance",
            "provider": "local",
            "retrieved_at": "2026-01-01T00:00:00Z",
        },
        "provenance": {
            "analyzer": "query_intent",
            "analyzer_version": "1.0",
            "method": "rule_based",
        },
        "confidence": 0.9,
        "relation": "supports",
        "derived_from": [],
        "captured_at": "2026-01-01T00:00:00Z",
        "status": status,
    }


def report(*, report_id: str = REPORT_ID, refs: list[str] | None = None) -> dict:
    refs = ["ev_001"] if refs is None else refs
    return {
        "report_id": report_id,
        "schema_version": "1.0",
        "lifecycle_stage": "research_complete",
        "search_intent": {
            "keyword": "consultant insurance",
            "primary_intent": "commercial",
            "confidence": 0.9,
        },
        "evidence_refs": {
            "intent": refs,
            "entity": [],
            "question": [],
            "business": [],
            "authority": [],
        },
    }


def test_valid_input_returns_normalized_validation_context() -> None:
    result = validate_intelligence_input(report(), [evidence()])

    assert result["report_id"] == REPORT_ID
    assert result["evidence_by_id"]["ev_001"]["status"] == "active"


def test_research_report_requires_non_empty_report_id() -> None:
    with pytest.raises(ValueError, match="report_id"):
        validate_intelligence_input(report(report_id=""), [evidence()])


def test_evidence_requires_matching_report_id() -> None:
    with pytest.raises(ValueError, match="report_id"):
        validate_intelligence_input(report(), [evidence(report_id="rr_other")])


def test_every_report_evidence_ref_must_resolve() -> None:
    with pytest.raises(ValueError, match="evidence_refs"):
        validate_intelligence_input(report(refs=["ev_missing"]), [evidence()])


def test_evidence_refs_must_not_be_empty() -> None:
    with pytest.raises(ValueError, match="evidence_refs"):
        validate_intelligence_input(report(refs=[]), [evidence()])


def test_duplicate_evidence_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_intelligence_input(report(), [evidence(), evidence()])


@pytest.mark.parametrize("status", ["superseded", "invalidated"])
def test_non_active_evidence_is_rejected_before_derivation(status: str) -> None:
    with pytest.raises(ValueError, match="status"):
        validate_intelligence_input(report(), [evidence(status=status)])


def test_unknown_evidence_status_is_rejected() -> None:
    with pytest.raises(ValueError, match="status"):
        validate_intelligence_input(report(), [evidence(status="unknown")])


def test_malformed_evidence_is_rejected() -> None:
    invalid = evidence()
    invalid.pop("claim")

    with pytest.raises(ValueError):
        validate_intelligence_input(report(), [invalid])


def test_evidence_input_is_not_mutated() -> None:
    report_input = report()
    evidence_input = [evidence()]
    before_report = copy.deepcopy(report_input)
    before_evidence = copy.deepcopy(evidence_input)

    validate_intelligence_input(report_input, evidence_input)

    assert report_input == before_report
    assert evidence_input == before_evidence


def test_unreferenced_extra_active_evidence_is_allowed() -> None:
    result = validate_intelligence_input(
        report(),
        [evidence(), evidence("ev_extra")],
    )

    assert set(result["evidence_by_id"]) == {"ev_001", "ev_extra"}
