from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_PATH = Path(__file__).parents[1] / "shared" / "schemas" / "final-optimization.schema.json"


def load_validator():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def valid_artifact():
    return {
        "optimization_id": "optimization_001",
        "schema_version": "1.0",
        "method_version": "v1",
        "lifecycle_stage": "optimization_ready",
        "seo_title": "Consultant Liability Insurance Guide",
        "meta_description": "A practical guide to consultant liability insurance coverage and costs.",
        "primary_keyword": "consultant liability insurance",
        "slug": "consultant-liability-insurance",
        "lineage": {
            "report_id": "report_001",
            "decision_id": "decision_001",
            "strategy_id": "strategy_001",
            "brief_id": "brief_001",
        },
    }


def assert_valid(instance):
    errors = list(load_validator().iter_errors(instance))
    assert errors == [], "\n".join(error.message for error in errors)


def assert_invalid(instance):
    assert list(load_validator().iter_errors(instance))


def test_schema_is_valid_draft_2020_12_schema():
    load_validator()


def test_valid_minimal_artifact_passes():
    assert_valid(valid_artifact())


def test_required_root_fields_are_enforced():
    for field in [
        "optimization_id",
        "schema_version",
        "method_version",
        "lifecycle_stage",
        "seo_title",
        "meta_description",
        "primary_keyword",
        "slug",
        "lineage",
    ]:
        artifact = valid_artifact()
        artifact.pop(field)
        assert_invalid(artifact)

@pytest.mark.parametrize("field", ["seo_title", "meta_description", "primary_keyword", "slug"])
def test_required_seo_values_reject_empty_and_whitespace(field):
    for value in ["", "   "]:
        artifact = valid_artifact()
        artifact[field] = value
        assert_invalid(artifact)

@pytest.mark.parametrize("field", ["report_id", "decision_id", "strategy_id", "brief_id"])
def test_required_lineage_fields_are_enforced(field):
    artifact = valid_artifact()
    artifact["lineage"].pop(field)
    assert_invalid(artifact)


def test_lineage_rejects_undeclared_fields():
    artifact = valid_artifact()
    artifact["lineage"]["draft_id"] = "draft_001"
    assert_invalid(artifact)


def test_root_rejects_undeclared_downstream_fields():
    artifact = valid_artifact()
    artifact["publish"] = True
    assert_invalid(artifact)


def test_lifecycle_is_exactly_optimization_ready():
    artifact = valid_artifact()
    artifact["lifecycle_stage"] = "delivery_ready"
    assert_invalid(artifact)


def test_schema_version_is_exactly_1_0():
    artifact = valid_artifact()
    artifact["schema_version"] = "2.0"
    assert_invalid(artifact)


def test_canonical_url_is_optional_but_must_be_a_uri_when_present():
    artifact = valid_artifact()
    artifact["canonical_url"] = "https://example.com/consultant-liability-insurance"
    assert_valid(artifact)

    artifact["canonical_url"] = "not a uri"
    assert_invalid(artifact)


def test_source_refs_are_optional_non_empty_strings():
    artifact = valid_artifact()
    artifact["source_refs"] = ["source_001", "source_002"]
    assert_valid(artifact)

    artifact["source_refs"] = ["   "]
    assert_invalid(artifact)


def test_audit_is_closed_in_v1():
    artifact = valid_artifact()
    artifact["audit"] = {}
    assert_valid(artifact)

    artifact["audit"] = {"validation_status": "validated"}
    assert_invalid(artifact)
