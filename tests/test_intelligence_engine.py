from __future__ import annotations

import copy

import pytest

from agents.intelligence.engine import build_intelligence


REPORT_ID = "rr_001"


def evidence(
    evidence_id: str = "ev_001",
    *,
    domain: str = "intent",
    relation: str = "supports",
    source_type: str = "query",
    value: str = "commercial",
) -> dict:
    return {
        "evidence_id": evidence_id,
        "report_id": REPORT_ID,
        "schema_version": "1.0",
        "type": "observation",
        "domain": domain,
        "subject": {"type": "keyword", "id": "consultant insurance"},
        "claim": {"type": "query_intent", "attribute": "primary_intent"},
        "value": {"type": "categorical", "data": value},
        "source": {
            "type": source_type,
            "source_id": "source-1",
            "provider": "local",
            "retrieved_at": "2026-01-01T00:00:00Z",
        },
        "provenance": {
            "analyzer": "test",
            "analyzer_version": "1.0",
            "method": "fixture",
        },
        "confidence": 0.9,
        "relation": relation,
        "derived_from": [],
        "captured_at": "2026-01-01T00:00:00Z",
        "status": "active",
    }


def report(*, refs: dict[str, list[str]] | None = None) -> dict:
    refs = refs or {
        "intent": ["ev_001"],
        "entity": ["ev_002"],
        "question": [],
        "business": ["ev_003"],
        "authority": [],
    }
    return {
        "report_id": REPORT_ID,
        "schema_version": "1.0",
        "lifecycle_stage": "research_complete",
        "search_intent": {
            "keyword": "consultant insurance",
            "primary_intent": "commercial",
            "confidence": 0.9,
        },
        "evidence_refs": refs,
    }


def test_engine_builds_schema_valid_intelligence() -> None:
    result = build_intelligence(
        report(),
        [
            evidence(),
            evidence("ev_002", domain="entity", source_type="serp", value="consultant"),
            evidence("ev_003", domain="business", source_type="business", value="cost"),
        ],
    )

    assert result["report_id"] == REPORT_ID
    assert result["lifecycle_stage"] == "intelligence_ready"
    assert result["intent_interpretation"]["evidence_refs"] == ["ev_001"]
    assert result["commercial_signals"][0]["evidence_refs"] == ["ev_003"]


def test_engine_is_deterministic() -> None:
    inputs = (
        report(),
        [
            evidence(),
            evidence("ev_002", domain="entity", source_type="serp", value="consultant"),
            evidence("ev_003", domain="business", source_type="business", value="cost"),
        ],
    )

    assert build_intelligence(*inputs) == build_intelligence(*copy.deepcopy(inputs))


def test_engine_fails_closed_before_derivation_for_invalid_input(monkeypatch: pytest.MonkeyPatch) -> None:
    import agents.intelligence.engine as engine

    def should_not_run(*args: object, **kwargs: object) -> dict:
        raise AssertionError("signal derivation ran before input validation")

    monkeypatch.setattr(engine, "_derive_intelligence", should_not_run)

    with pytest.raises(ValueError):
        build_intelligence(
            report(),
            [evidence("ev_001", relation="supports"), evidence("ev_001", domain="entity")],
        )


def test_engine_fails_closed_when_intent_evidence_is_missing() -> None:
    invalid_report = report(
        refs={
            "intent": [],
            "entity": ["ev_002"],
            "question": [],
            "business": [],
            "authority": [],
        }
    )

    with pytest.raises(ValueError, match="intent evidence_refs"):
        build_intelligence(
            invalid_report,
            [evidence("ev_002", domain="entity")],
        )


def test_contradictory_evidence_raises_ambiguity() -> None:
    result = build_intelligence(
        report(
            refs={
                "intent": ["ev_001"],
                "entity": [],
                "question": [],
                "business": ["ev_002"],
                "authority": [],
            }
        ),
        [
            evidence("ev_001", value="commercial"),
            evidence("ev_002", domain="business", relation="contradicts", value="non-commercial"),
        ],
    )

    assert result["ambiguity"]["level"] == "high"
    assert result["ambiguity"]["evidence_refs"] == ["ev_002"]


def test_engine_does_not_create_downstream_ids() -> None:
    result = build_intelligence(
        report(),
        [
            evidence(),
            evidence("ev_002", domain="entity"),
            evidence("ev_003", domain="business", value="cost"),
        ],
    )

    for field in ("recommendation_id", "decision_id", "strategy_id", "brief_id", "draft_id", "quality_id"):
        assert field not in result


def test_engine_does_not_mutate_inputs() -> None:
    report_input = report()
    evidence_input = [
        evidence(),
        evidence("ev_002", domain="entity"),
        evidence("ev_003", domain="business", value="cost"),
    ]
    before_report = copy.deepcopy(report_input)
    before_evidence = copy.deepcopy(evidence_input)

    build_intelligence(report_input, evidence_input)

    assert report_input == before_report
    assert evidence_input == before_evidence
