import json
from pathlib import Path

import pytest

from agents.research.analyzers.query_intent import classify_query_intent
from agents.research.evidence.query_intent import build_query_intent_evidence

jsonschema = pytest.importorskip("jsonschema")
SCHEMA_PATH = Path("shared/schemas/evidence.schema.json")


def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_builder_converts_query_intent_to_canonical_evidence():
    analysis = classify_query_intent("expat health insurance")

    evidence = build_query_intent_evidence(
        analysis,
        report_id="rr_001",
        evidence_id="ev_001",
        captured_at="2026-08-17T00:00:00Z",
    )

    assert evidence["evidence_id"] == "ev_001"
    assert evidence["report_id"] == "rr_001"
    assert evidence["domain"] == "intent"
    assert evidence["claim"] == {
        "type": "query_intent",
        "attribute": "primary_intent",
    }
    assert evidence["value"]["data"] == analysis["primary_intent"]
    assert evidence["confidence"] == analysis["confidence"]
    assert evidence["derived_from"] == []


def test_builder_output_matches_evidence_schema():
    analysis = classify_query_intent("expat health insurance")
    evidence = build_query_intent_evidence(
        analysis,
        report_id="rr_001",
        evidence_id="ev_001",
        captured_at="2026-08-17T00:00:00Z",
    )

    jsonschema.Draft202012Validator(load_schema()).validate(evidence)


def test_builder_preserves_explicit_capture_time():
    analysis = classify_query_intent("expat health insurance")
    evidence = build_query_intent_evidence(
        analysis,
        report_id="rr_001",
        captured_at="2026-08-17T00:00:00Z",
    )

    assert evidence["captured_at"] == "2026-08-17T00:00:00Z"
    assert evidence["source"]["retrieved_at"] == "2026-08-17T00:00:00Z"


def test_builder_default_id_is_deterministic_for_report():
    analysis = classify_query_intent("expat health insurance")

    first = build_query_intent_evidence(analysis, report_id="rr_001")
    second = build_query_intent_evidence(analysis, report_id="rr_001")

    assert first["evidence_id"] == second["evidence_id"]
    assert first["evidence_id"].startswith("ev_")


def test_builder_rejects_missing_report_id():
    analysis = classify_query_intent("expat health insurance")

    with pytest.raises(ValueError, match="report_id is required"):
        build_query_intent_evidence(analysis, report_id="")


def test_builder_rejects_invalid_confidence():
    analysis = {
        "keyword": "expat health insurance",
        "primary_intent": "Informational",
        "confidence": 1.1,
    }

    with pytest.raises(ValueError, match="confidence must be between"):
        build_query_intent_evidence(analysis, report_id="rr_001")
