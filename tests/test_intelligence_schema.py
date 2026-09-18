from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "shared" / "schemas" / "intelligence.schema.json"


def load_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def valid_artifact() -> dict:
    return {
        "intelligence_id": "intelligence_001",
        "report_id": "rr_001",
        "intent_interpretation": {
            "summary": "The topic primarily reflects commercial research intent.",
            "evidence_refs": ["ev_intent_001"],
        },
        "ambiguity": {
            "level": "medium",
            "explanation": "The query has more than one plausible interpretation.",
            "evidence_refs": ["ev_intent_001"],
        },
        "topic_signals": [
            {"summary": "Professional liability is a central topic signal.", "evidence_refs": ["ev_topic_001"]}
        ],
        "source_type_signals": [
            {"summary": "Commercial provider sources are prominent.", "evidence_refs": ["ev_source_001"]}
        ],
        "commercial_signals": [
            {"summary": "Coverage and provider comparison are commercial signals.", "evidence_refs": ["ev_commercial_001"]}
        ],
        "decision_signals": [
            {"summary": "Coverage limits are a consideration for downstream evaluation.", "evidence_refs": ["ev_decision_001"]}
        ],
        "unsupported_or_insufficient": [
            "No sufficient evidence to generalize pricing across all consultant types."
        ],
        "schema_version": "1.0",
        "method_version": "v1",
        "lifecycle_stage": "intelligence_ready",
    }


def assert_valid(instance: dict) -> None:
    errors = list(load_validator().iter_errors(instance))
    assert errors == [], "\n".join(error.message for error in errors)


def assert_invalid(instance: dict) -> None:
    assert list(load_validator().iter_errors(instance))


def test_schema_is_valid_draft_2020_12_schema() -> None:
    load_validator()


def test_valid_intelligence_artifact_passes_schema() -> None:
    assert_valid(valid_artifact())


def test_all_contract_root_fields_are_required() -> None:
    for field in [
        "intelligence_id",
        "report_id",
        "intent_interpretation",
        "ambiguity",
        "topic_signals",
        "source_type_signals",
        "commercial_signals",
        "decision_signals",
        "unsupported_or_insufficient",
        "schema_version",
        "method_version",
        "lifecycle_stage",
    ]:
        instance = valid_artifact()
        instance.pop(field)
        assert_invalid(instance)


@pytest.mark.parametrize("field", ["intelligence_id", "report_id", "schema_version", "method_version"])
def test_required_identifiers_and_versions_reject_empty_values(field: str) -> None:
    instance = valid_artifact()
    instance[field] = ""
    assert_invalid(instance)


def test_lifecycle_stage_is_exactly_intelligence_ready() -> None:
    instance = valid_artifact()
    instance["lifecycle_stage"] = "research_complete"
    assert_invalid(instance)


def test_ambiguity_level_is_constrained() -> None:
    instance = valid_artifact()
    instance["ambiguity"]["level"] = "unknown"
    assert_invalid(instance)


def test_each_evidence_signal_requires_non_empty_evidence_refs() -> None:
    signal_fields = [
        "intent_interpretation",
        "topic_signals",
        "source_type_signals",
        "commercial_signals",
        "decision_signals",
    ]
    for field in signal_fields:
        instance = valid_artifact()
        if isinstance(instance[field], list):
            instance[field][0]["evidence_refs"] = []
        else:
            instance[field]["evidence_refs"] = []
        assert_invalid(instance)


def test_evidence_refs_must_be_unique() -> None:
    instance = valid_artifact()
    instance["topic_signals"][0]["evidence_refs"] = ["ev_001", "ev_001"]
    assert_invalid(instance)


def test_evidence_refs_reject_empty_strings() -> None:
    instance = valid_artifact()
    instance["commercial_signals"][0]["evidence_refs"] = [""]
    assert_invalid(instance)


def test_evidence_signal_requires_summary() -> None:
    instance = valid_artifact()
    instance["decision_signals"][0].pop("summary")
    assert_invalid(instance)


def test_unsupported_or_insufficient_requires_strings() -> None:
    instance = valid_artifact()
    instance["unsupported_or_insufficient"] = [123]
    assert_invalid(instance)


def test_root_rejects_downstream_ownership_fields() -> None:
    for field in ["recommendation_id", "decision_id", "strategy_id"]:
        instance = valid_artifact()
        instance[field] = "must-not-exist"
        assert_invalid(instance)


def test_root_rejects_production_lineage_fields_beyond_report_id() -> None:
    for field in ["brief_id", "draft_id", "quality_id"]:
        instance = valid_artifact()
        instance[field] = "must-not-exist"
        assert_invalid(instance)


def test_evidence_signal_rejects_undeclared_fields() -> None:
    instance = valid_artifact()
    instance["topic_signals"][0]["decision"] = "must-not-exist"
    assert_invalid(instance)


def test_ambiguity_rejects_undeclared_fields() -> None:
    instance = valid_artifact()
    instance["ambiguity"]["intent_model"] = "must-not-exist"
    assert_invalid(instance)


def test_empty_signal_collections_are_allowed_by_schema() -> None:
    instance = valid_artifact()
    instance["topic_signals"] = []
    instance["source_type_signals"] = []
    instance["commercial_signals"] = []
    instance["decision_signals"] = []
    assert_valid(instance)


def test_unsupported_or_insufficient_may_be_empty_but_is_required() -> None:
    instance = valid_artifact()
    instance["unsupported_or_insufficient"] = []
    assert_valid(instance)


def test_schema_validation_does_not_mutate_artifact() -> None:
    instance = valid_artifact()
    before = copy.deepcopy(instance)
    assert_valid(instance)
    assert instance == before
