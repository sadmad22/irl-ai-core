from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate


SCHEMA_PATH = Path("shared/schemas/production-stabilization.schema.json")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _base_result() -> dict:
    check = {"status": "passed", "message": "ok"}
    return {
        "stabilization_id": "stabilization_0123456789abcdef",
        "schema_version": "1.0",
        "project_name": "m7-consultant-liability",
        "production_id": "production_0123456789abcdef",
        "orchestration_id": "orchestration_0123456789abcdef",
        "job_id": "job_0123456789abcdef",
        "run_id": "run_0123456789abcdef",
        "outcome": "passed",
        "checks": {
            "article_package": dict(check),
            "orchestration": dict(check),
            "production_job": dict(check),
            "controlled_production": dict(check),
            "publication_boundary": dict(check),
        },
        "audit": {
            "method": "production_stabilization",
            "version": "v1",
            "validation_status": "validated",
        },
    }


def test_valid_passed_result() -> None:
    validate(_base_result(), _schema())


def test_invalid_stabilization_id_is_rejected() -> None:
    instance = _base_result()
    instance["stabilization_id"] = "stabilization_bad"
    with pytest.raises(ValidationError):
        validate(instance, _schema())


def test_invalid_outcome_is_rejected() -> None:
    instance = _base_result()
    instance["outcome"] = "failed"
    with pytest.raises(ValidationError):
        validate(instance, _schema())


def test_passed_result_cannot_contain_failed_check() -> None:
    instance = _base_result()
    instance["checks"]["production_job"]["status"] = "failed"
    with pytest.raises(ValidationError):
        validate(instance, _schema())


def test_unexpected_field_is_rejected() -> None:
    instance = _base_result()
    instance["wordpress_password"] = "must-not-exist"
    with pytest.raises(ValidationError):
        validate(instance, _schema())


def test_audit_metadata_is_fixed() -> None:
    instance = _base_result()
    instance["audit"]["method"] = "other"
    with pytest.raises(ValidationError):
        validate(instance, _schema())
