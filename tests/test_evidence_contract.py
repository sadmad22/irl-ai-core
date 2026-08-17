import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

SCHEMA_PATH = Path("shared/schemas/evidence.schema.json")

VALID_EVIDENCE = {
    "evidence_id": "ev_001",
    "report_id": "rr_001",
    "schema_version": "1.0",
    "type": "observation",
    "domain": "intent",
    "subject": {"type": "keyword", "id": "kw_expat-health-insurance"},
    "claim": {"type": "query_intent", "attribute": "primary_intent"},
    "value": {"type": "categorical", "data": "Informational"},
    "source": {
        "type": "query",
        "source_id": "kw_expat-health-insurance",
        "provider": "local",
        "retrieved_at": "2026-08-17T00:00:00Z",
    },
    "provenance": {
        "analyzer": "query_intent",
        "analyzer_version": "1.0",
        "method": "rule_based",
    },
    "confidence": 1.0,
    "relation": "supports",
    "derived_from": [],
    "captured_at": "2026-08-17T00:00:00Z",
    "status": "active",
}


def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_valid_observation_matches_contract():
    jsonschema.Draft202012Validator(load_schema()).validate(VALID_EVIDENCE)


def test_derived_evidence_supports_lineage():
    evidence = {
        **VALID_EVIDENCE,
        "evidence_id": "ev_002",
        "type": "derived",
        "domain": "serp",
        "claim": {"type": "serp_intent", "attribute": "dominant_intent"},
        "value": {"type": "categorical", "data": "Informational"},
        "source": {
            "type": "derived",
            "source_id": None,
            "provider": None,
            "retrieved_at": None,
        },
        "provenance": {
            "analyzer": "serp_intent",
            "analyzer_version": "1.0",
            "method": "rule_based",
        },
        "confidence": 0.6337,
        "derived_from": ["ev_001"],
    }

    jsonschema.Draft202012Validator(load_schema()).validate(evidence)


def test_confidence_must_be_between_zero_and_one():
    evidence = {**VALID_EVIDENCE, "confidence": 1.01}

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(load_schema()).validate(evidence)


def test_unknown_evidence_type_is_rejected():
    evidence = {**VALID_EVIDENCE, "type": "decision"}

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(load_schema()).validate(evidence)


def test_unknown_domain_remains_allowed_for_future_extension():
    evidence = {**VALID_EVIDENCE, "domain": "authority"}

    jsonschema.Draft202012Validator(load_schema()).validate(evidence)
