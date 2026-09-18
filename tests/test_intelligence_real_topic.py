from __future__ import annotations

from agents.intelligence.project_integration import (
    _normalize_evidence_provenance,
    _normalize_evidence_source,
    build_intelligence_from_project,
)
from agents.research import production_orchestrator as orchestrator


PROJECT = "expat-health-insurance"


def test_real_topic_builds_canonical_intelligence_without_mutating_research():
    intelligence = build_intelligence_from_project(PROJECT)

    assert intelligence["report_id"] == "rr_expat-health-insurance"
    assert intelligence["intelligence_id"].startswith("int_")
    assert intelligence["lifecycle_stage"] == "intelligence_ready"
    assert intelligence["intent_interpretation"]["evidence_refs"]
    assert intelligence["topic_signals"]
    assert intelligence["commercial_signals"]
    assert intelligence["decision_signals"]

    downstream_ids = (
        "recommendation_id",
        "decision_id",
        "strategy_id",
        "brief_id",
        "draft_id",
        "quality_id",
    )
    assert all(field not in intelligence for field in downstream_ids)


def test_real_topic_intelligence_is_accepted_as_canonical_orchestrator_stage():
    intelligence = build_intelligence_from_project(PROJECT)
    result = {
        "research_report": {"report_id": intelligence["report_id"]},
        "intelligence": intelligence,
        "content_brief": {"brief_id": "brief_123"},
    }

    assert orchestrator._completed_stages(result) == [
        "research",
        "intelligence",
        "configuration",
        "structure",
    ]


def test_content_brief_does_not_supply_intelligence_for_real_topic():
    result = {
        "research_report": {"report_id": "rr_expat-health-insurance"},
        "content_brief": {"brief_id": "brief_123"},
    }

    assert orchestrator._completed_stages(result) == [
        "research",
        "configuration",
        "structure",
    ]


def test_legacy_evidence_version_is_normalized_only_in_runtime_copy():
    evidence = {
        "evidence_id": "ev_legacy",
        "provenance": {
            "analyzer": "entity",
            "method": "entity-v1",
            "version": "v1",
        },
    }

    normalized = _normalize_evidence_provenance(evidence)

    assert normalized["provenance"]["analyzer_version"] == "v1"
    assert "version" not in normalized["provenance"]
    assert evidence["provenance"]["version"] == "v1"
    assert "analyzer_version" not in evidence["provenance"]


def test_canonical_evidence_analyzer_version_is_preserved():
    evidence = {
        "evidence_id": "ev_canonical",
        "provenance": {
            "analyzer": "serp-intent",
            "method": "serp-intent-v1",
            "analyzer_version": "1.0",
        },
    }

    normalized = _normalize_evidence_provenance(evidence)

    assert normalized == evidence
    assert normalized["provenance"]["analyzer_version"] == "1.0"


def test_conflicting_evidence_provenance_versions_fail_closed():
    evidence = {
        "evidence_id": "ev_conflict",
        "provenance": {
            "analyzer": "entity",
            "method": "entity-v1",
            "version": "v1",
            "analyzer_version": "1.0",
        },
    }

    try:
        _normalize_evidence_provenance(evidence)
    except ValueError as exc:
        assert "Conflicting Evidence provenance version fields" in str(exc)
    else:
        raise AssertionError("Expected conflicting provenance versions to fail closed")


def test_legacy_research_artifact_source_is_normalized_losslessly_in_runtime_copy():
    evidence = {
        "evidence_id": "ev_legacy_source",
        "source": {
            "type": "research_artifact",
            "project": "expat-health-insurance",
            "artifact": "serp-analysis.json",
        },
    }

    normalized = _normalize_evidence_source(evidence)

    assert normalized["source"] == {
        "type": "research_artifact",
        "source_id": "research/expat-health-insurance/serp-analysis.json",
        "provider": "local",
        "retrieved_at": None,
    }
    assert evidence["source"]["project"] == "expat-health-insurance"
    assert evidence["source"]["artifact"] == "serp-analysis.json"


def test_canonical_evidence_source_is_preserved():
    evidence = {
        "evidence_id": "ev_canonical_source",
        "source": {
            "type": "query",
            "source_id": "expat health insurance",
            "provider": "local",
            "retrieved_at": "2026-08-21T12:45:59Z",
        },
    }

    normalized = _normalize_evidence_source(evidence)

    assert normalized == evidence


def test_conflicting_evidence_source_shapes_fail_closed():
    evidence = {
        "evidence_id": "ev_source_conflict",
        "source": {
            "type": "research_artifact",
            "project": "expat-health-insurance",
            "artifact": "serp-analysis.json",
            "source_id": "unexpected",
            "provider": "local",
            "retrieved_at": None,
        },
    }

    try:
        _normalize_evidence_source(evidence)
    except ValueError as exc:
        assert "Conflicting Evidence source fields" in str(exc)
    else:
        raise AssertionError("Expected conflicting source shapes to fail closed")


def test_unsupported_legacy_evidence_source_type_fails_closed():
    evidence = {
        "evidence_id": "ev_source_type",
        "source": {
            "type": "external_artifact",
            "project": "expat-health-insurance",
            "artifact": "serp-analysis.json",
        },
    }

    try:
        _normalize_evidence_source(evidence)
    except ValueError as exc:
        assert "Legacy Evidence source type is unsupported" in str(exc)
    else:
        raise AssertionError("Expected unsupported legacy source type to fail closed")
