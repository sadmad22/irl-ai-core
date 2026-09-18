from __future__ import annotations

import copy

import pytest

from agents.intelligence.traceability import validate_intelligence_traceability


REPORT_ID = "rr_001"


def evidence(
    evidence_id: str = "ev_001",
    *,
    report_id: str = REPORT_ID,
    status: str = "active",
) -> dict:
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


def report() -> dict:
    return {
        "report_id": REPORT_ID,
        "evidence_refs": {
            "intent": ["ev_001"],
            "entity": [],
            "question": [],
            "business": [],
            "authority": [],
        },
    }


def intelligence() -> dict:
    return {
        "report_id": REPORT_ID,
        "intent_interpretation": {
            "summary": "Canonical intent interpretation.",
            "evidence_refs": ["ev_001"],
        },
        "ambiguity": {
            "level": "low",
            "explanation": "No ambiguity detected.",
            "evidence_refs": ["ev_001"],
        },
        "topic_signals": [],
        "source_type_signals": [],
        "commercial_signals": [],
        "decision_signals": [],
    }


def test_valid_intelligence_traces_to_research_evidence() -> None:
    validate_intelligence_traceability(
        intelligence(),
        report(),
        {"ev_001": evidence()},
    )


def test_traceability_rejects_reference_outside_research_report() -> None:
    invalid = intelligence()
    invalid["intent_interpretation"]["evidence_refs"] = ["ev_other"]

    with pytest.raises(ValueError, match="outside ResearchReport"):
        validate_intelligence_traceability(
            invalid,
            report(),
            {"ev_other": evidence("ev_other")},
        )


def test_traceability_rejects_unresolved_evidence() -> None:
    invalid = intelligence()
    invalid["intent_interpretation"]["evidence_refs"] = ["ev_missing"]
    invalid["ambiguity"]["evidence_refs"] = ["ev_missing"]
    research = report()
    research["evidence_refs"]["intent"] = ["ev_missing"]

    with pytest.raises(ValueError, match="unresolved Evidence"):
        validate_intelligence_traceability(
            invalid,
            research,
            {"ev_001": evidence()},
        )


def test_traceability_rejects_mismatched_evidence_report_id() -> None:
    with pytest.raises(ValueError, match="mismatched report_id"):
        validate_intelligence_traceability(
            intelligence(),
            report(),
            {"ev_001": evidence(report_id="rr_other")},
        )


def test_traceability_rejects_non_active_evidence() -> None:
    with pytest.raises(ValueError, match="non-active Evidence"):
        validate_intelligence_traceability(
            intelligence(),
            report(),
            {"ev_001": evidence(status="superseded")},
        )


def test_traceability_does_not_mutate_inputs() -> None:
    artifact = intelligence()
    research = report()
    evidence_map = {"ev_001": evidence()}
    before = copy.deepcopy((artifact, research, evidence_map))

    validate_intelligence_traceability(artifact, research, evidence_map)

    assert (artifact, research, evidence_map) == before
