import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.evidence.authority import build_authority_evidence
from agents.research.evidence.business import build_business_evidence
from agents.research.evidence.entity import build_entity_evidence
from agents.research.evidence.question import build_question_evidence


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "shared/schemas/evidence.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)

SOURCE = {"type": "research", "source_id": "src_001", "provider": "mock", "retrieved_at": "2026-08-17T20:00:00+00:00"}
PROVENANCE = {"analyzer": "domain-test", "analyzer_version": "1.0", "method": "observation"}


def assert_valid(evidence):
    VALIDATOR.validate(evidence)


def test_entity_presence_and_relevance_are_valid_and_deterministic():
    first = build_entity_evidence(
        report_id="rr_001", entity_id="cigna", entity_type="organization", mentioned=True,
        relevance=0.9, source=SOURCE, provenance=PROVENANCE, confidence=1.0,
        captured_at="2026-08-17T20:00:00+00:00",
    )
    second = build_entity_evidence(
        report_id="rr_001", entity_id="cigna", entity_type="organization", mentioned=True,
        relevance=0.9, source=SOURCE, provenance=PROVENANCE, confidence=1.0,
        captured_at="2026-08-17T20:00:00+00:00",
    )
    assert len(first) == 2
    assert [item["evidence_id"] for item in first] == [item["evidence_id"] for item in second]
    for item in first:
        assert_valid(item)


def test_entity_rejects_invalid_relevance():
    with pytest.raises(ValueError):
        build_entity_evidence(
            report_id="rr_001", entity_id="cigna", entity_type="organization", mentioned=True,
            relevance=1.1, source=SOURCE, provenance=PROVENANCE, confidence=1.0,
        )


def test_question_frequency_is_valid():
    evidence = build_question_evidence(
        report_id="rr_001", subject_type="keyword", subject_id="expat-health-insurance",
        question_count=14, source=SOURCE, provenance=PROVENANCE, confidence=0.95,
        captured_at="2026-08-17T20:00:00+00:00",
    )
    assert evidence["domain"] == "question"
    assert evidence["value"]["data"] == 14
    assert_valid(evidence)


def test_question_rejects_negative_count():
    with pytest.raises(ValueError):
        build_question_evidence(
            report_id="rr_001", subject_type="keyword", subject_id="kw",
            question_count=-1, source=SOURCE, provenance=PROVENANCE, confidence=1.0,
        )


def test_business_claims_are_valid():
    evidence = build_business_evidence(
        report_id="rr_001", subject_type="keyword", subject_id="expat-health-insurance",
        claim_type="affiliate_potential", value="high", source=SOURCE,
        provenance=PROVENANCE, confidence=0.8, captured_at="2026-08-17T20:00:00+00:00",
    )
    assert evidence["domain"] == "business"
    assert_valid(evidence)


def test_business_rejects_unknown_claim():
    with pytest.raises(ValueError):
        build_business_evidence(
            report_id="rr_001", subject_type="keyword", subject_id="kw",
            claim_type="decision", value="approved", source=SOURCE,
            provenance=PROVENANCE, confidence=1.0,
        )


def test_authority_score_is_valid():
    evidence = build_authority_evidence(
        report_id="rr_001", subject_type="keyword", subject_id="expat-health-insurance",
        claim_type="authority_score", score=0.78, source=SOURCE,
        provenance=PROVENANCE, confidence=0.9, captured_at="2026-08-17T20:00:00+00:00",
    )
    assert evidence["domain"] == "authority"
    assert evidence["value"]["data"] == 0.78
    assert_valid(evidence)


def test_authority_rejects_out_of_range_score():
    with pytest.raises(ValueError):
        build_authority_evidence(
            report_id="rr_001", subject_type="keyword", subject_id="kw",
            claim_type="authority_score", score=1.2, source=SOURCE,
            provenance=PROVENANCE, confidence=1.0,
        )
