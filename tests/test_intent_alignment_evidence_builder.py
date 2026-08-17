import json
from pathlib import Path

import pytest

from agents.research.analyzers.intent_alignment import analyze_intent_alignment
from agents.research.evidence.intent_alignment import build_intent_alignment_evidence

jsonschema = pytest.importorskip("jsonschema")
SCHEMA_PATH = Path("shared/schemas/evidence.schema.json")


def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def sample_analysis():
    return analyze_intent_alignment(
        {"keyword": "expat health insurance", "primary_intent": "Informational"},
        {
            "keyword": "expat health insurance",
            "dominant_intent": "Informational",
            "mixed_intent": True,
            "dominant_confidence": 0.6337,
            "intent_distribution": {
                "Commercial": 0.2747,
                "Informational": 0.6337,
                "Transactional": 0.0916,
            },
        },
    )


def test_builder_creates_derived_alignment_evidence():
    analysis = sample_analysis()
    evidence = build_intent_alignment_evidence(
        analysis,
        report_id="rr_001",
        query_intent_evidence_id="ev_query_001",
        serp_intent_evidence_ids=["ev_serp_dominant_001", "ev_serp_mixed_001"],
        captured_at="2026-08-17T00:00:00Z",
    )

    assert evidence["report_id"] == "rr_001"
    assert evidence["type"] == "derived"
    assert evidence["domain"] == "intent"
    assert evidence["claim"] == {
        "type": "intent_alignment",
        "attribute": "alignment",
    }
    assert evidence["value"]["data"] == "mixed"
    assert evidence["confidence"] == 0.6337
    assert evidence["derived_from"] == [
        "ev_query_001",
        "ev_serp_dominant_001",
        "ev_serp_mixed_001",
    ]


def test_builder_output_matches_evidence_schema():
    evidence = build_intent_alignment_evidence(
        sample_analysis(),
        report_id="rr_001",
        query_intent_evidence_id="ev_query_001",
        serp_intent_evidence_ids=["ev_serp_dominant_001", "ev_serp_mixed_001"],
        captured_at="2026-08-17T00:00:00Z",
    )

    jsonschema.Draft202012Validator(load_schema()).validate(evidence)


def test_builder_deduplicates_lineage_without_changing_order():
    evidence = build_intent_alignment_evidence(
        sample_analysis(),
        report_id="rr_001",
        query_intent_evidence_id="ev_query_001",
        serp_intent_evidence_ids=[
            "ev_serp_dominant_001",
            "ev_serp_dominant_001",
            "ev_serp_mixed_001",
        ],
        captured_at="2026-08-17T00:00:00Z",
    )

    assert evidence["derived_from"] == [
        "ev_query_001",
        "ev_serp_dominant_001",
        "ev_serp_mixed_001",
    ]


def test_builder_supports_misaligned_alignment():
    analysis = analyze_intent_alignment(
        {"keyword": "expat health insurance", "primary_intent": "Informational"},
        {
            "keyword": "expat health insurance",
            "dominant_intent": "Commercial",
            "mixed_intent": False,
            "dominant_confidence": 0.8,
        },
    )

    evidence = build_intent_alignment_evidence(
        analysis,
        report_id="rr_001",
        query_intent_evidence_id="ev_query_001",
        serp_intent_evidence_ids=["ev_serp_dominant_001"],
        captured_at="2026-08-17T00:00:00Z",
    )

    assert evidence["value"]["data"] == "misaligned"
    assert evidence["confidence"] == 0.8


def test_builder_rejects_missing_upstream_lineage():
    analysis = sample_analysis()

    with pytest.raises(ValueError, match="query_intent_evidence_id is required"):
        build_intent_alignment_evidence(
            analysis,
            report_id="rr_001",
            query_intent_evidence_id="",
            serp_intent_evidence_ids=["ev_serp_001"],
        )

    with pytest.raises(ValueError, match="non-empty list"):
        build_intent_alignment_evidence(
            analysis,
            report_id="rr_001",
            query_intent_evidence_id="ev_query_001",
            serp_intent_evidence_ids=[],
        )


def test_builder_rejects_invalid_confidence():
    analysis = sample_analysis()
    analysis["confidence"] = 1.1

    with pytest.raises(ValueError, match="confidence must be between"):
        build_intent_alignment_evidence(
            analysis,
            report_id="rr_001",
            query_intent_evidence_id="ev_query_001",
            serp_intent_evidence_ids=["ev_serp_001"],
        )
