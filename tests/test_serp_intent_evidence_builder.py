import json
from pathlib import Path

import pytest

from agents.research.analyzers.serp_intent import analyze_serp_intent
from agents.research.evidence.serp_intent import build_serp_intent_evidence

jsonschema = pytest.importorskip("jsonschema")
SCHEMA_PATH = Path("shared/schemas/evidence.schema.json")


def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def sample_serp_analysis():
    serp_data = {
        "keyword": "expat health insurance",
        "country": "US",
        "language": "en",
        "results": [
            {
                "position": 1,
                "domain": "example.com",
                "title": "Expat Health Insurance Guide",
                "url": "https://example.com/expat-health-insurance",
            },
            {
                "position": 2,
                "domain": "example.org",
                "title": "Best Expat Health Insurance Plans",
                "url": "https://example.org/insurance",
            },
            {
                "position": 3,
                "domain": "example.net",
                "title": "How Expat Health Insurance Works",
                "url": "https://example.net/guide",
            },
        ],
    }
    return analyze_serp_intent(serp_data)


def test_builder_returns_result_and_aggregate_evidence():
    analysis = sample_serp_analysis()

    evidence = build_serp_intent_evidence(
        analysis,
        report_id="rr_001",
        captured_at="2026-08-17T00:00:00Z",
    )

    assert len(evidence) == len(analysis["results"]) + 3
    assert all(item["report_id"] == "rr_001" for item in evidence)

    result_items = [item for item in evidence if item["type"] == "observation"]
    aggregate_items = [item for item in evidence if item["type"] == "derived"]

    assert len(result_items) == len(analysis["results"])
    assert len(aggregate_items) == 3


def test_builder_preserves_result_intent_and_confidence():
    analysis = sample_serp_analysis()
    evidence = build_serp_intent_evidence(
        analysis,
        report_id="rr_001",
        captured_at="2026-08-17T00:00:00Z",
    )

    result_items = [item for item in evidence if item["type"] == "observation"]

    for item, result in zip(result_items, analysis["results"]):
        assert item["domain"] == "serp"
        assert item["claim"]["attribute"] == "result_intent"
        assert item["value"]["data"] == result["intent"]
        assert item["confidence"] == result["confidence"]
        assert item["derived_from"] == []


def test_aggregate_evidence_has_lineage_to_result_evidence():
    analysis = sample_serp_analysis()
    evidence = build_serp_intent_evidence(
        analysis,
        report_id="rr_001",
        captured_at="2026-08-17T00:00:00Z",
    )

    result_ids = {
        item["evidence_id"]
        for item in evidence
        if item["type"] == "observation"
    }

    distribution = next(
        item for item in evidence
        if item["claim"]["attribute"] == "intent_distribution"
    )
    dominant = next(
        item for item in evidence
        if item["claim"]["attribute"] == "dominant_intent"
    )
    mixed = next(
        item for item in evidence
        if item["claim"]["attribute"] == "mixed_intent"
    )

    assert set(distribution["derived_from"]) == result_ids
    assert set(mixed["derived_from"]) == result_ids
    assert set(dominant["derived_from"]).issubset(result_ids)
    assert dominant["derived_from"]


def test_all_builder_outputs_match_evidence_schema():
    analysis = sample_serp_analysis()
    evidence = build_serp_intent_evidence(
        analysis,
        report_id="rr_001",
        captured_at="2026-08-17T00:00:00Z",
    )
    validator = jsonschema.Draft202012Validator(load_schema())

    for item in evidence:
        validator.validate(item)


def test_builder_rejects_missing_report_id():
    analysis = sample_serp_analysis()

    with pytest.raises(ValueError, match="report_id is required"):
        build_serp_intent_evidence(analysis, report_id="")


def test_builder_rejects_invalid_result_confidence():
    analysis = sample_serp_analysis()
    analysis["results"][0]["confidence"] = 1.1

    with pytest.raises(ValueError, match="confidence must be between"):
        build_serp_intent_evidence(analysis, report_id="rr_001")


def test_builder_is_deterministic_for_same_input():
    analysis = sample_serp_analysis()

    first = build_serp_intent_evidence(
        analysis,
        report_id="rr_001",
        captured_at="2026-08-17T00:00:00Z",
    )
    second = build_serp_intent_evidence(
        analysis,
        report_id="rr_001",
        captured_at="2026-08-17T00:00:00Z",
    )

    assert first == second
