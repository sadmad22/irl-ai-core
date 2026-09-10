from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate


SCHEMA_PATH = Path("shared/schemas/controlled-production.schema.json")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _base_run() -> dict:
    return {
        "run_id": "run_0123456789abcdef",
        "schema_version": "1.0",
        "project_name": "m7-consultant-liability",
        "topic": "Consultant Liability Insurance",
        "production_id": "production_0123456789abcdef",
        "orchestration_id": "orchestration_0123456789abcdef",
        "status": "queued",
        "delivery": {
            "status": "not_started",
            "delivery_id": None,
            "post_id": None,
            "edit_url": None,
            "remote_status": None,
            "error": None,
        },
        "human_review": {"required": True, "status": "pending"},
        "publication": {
            "mode": "wordpress_draft",
            "publish": False,
            "human_approval_required": True,
        },
        "audit": {
            "method": "controlled_production",
            "version": "v1",
            "validation_status": "validated",
        },
    }


def test_valid_queued_run() -> None:
    validate(_base_run(), _schema())


def test_valid_human_review_run_requires_delivered_draft() -> None:
    instance = _base_run()
    instance["status"] = "human_review"
    instance["delivery"] = {
        "status": "delivered",
        "delivery_id": "wpconn_0123456789abcdef",
        "post_id": 123,
        "edit_url": "https://example.test/wp-admin/post.php?post=123&action=edit",
        "remote_status": "draft",
        "error": None,
    }
    validate(instance, _schema())


def test_approved_run_requires_human_approval_and_draft_delivery() -> None:
    instance = _base_run()
    instance["status"] = "approved"
    instance["human_review"]["status"] = "approved"
    instance["delivery"] = {
        "status": "delivered",
        "delivery_id": "wpconn_0123456789abcdef",
        "post_id": 123,
        "edit_url": "https://example.test/wp-admin/post.php?post=123&action=edit",
        "remote_status": "draft",
        "error": None,
    }
    validate(instance, _schema())


def test_publish_true_is_rejected() -> None:
    instance = _base_run()
    instance["publication"]["publish"] = True
    with pytest.raises(ValidationError):
        validate(instance, _schema())


def test_non_draft_publication_mode_is_rejected() -> None:
    instance = _base_run()
    instance["publication"]["mode"] = "wordpress_publish"
    with pytest.raises(ValidationError):
        validate(instance, _schema())


def test_approved_without_draft_delivery_is_rejected() -> None:
    instance = _base_run()
    instance["status"] = "approved"
    instance["human_review"]["status"] = "approved"
    with pytest.raises(ValidationError):
        validate(instance, _schema())


def test_human_review_without_delivery_is_rejected() -> None:
    instance = _base_run()
    instance["status"] = "human_review"
    with pytest.raises(ValidationError):
        validate(instance, _schema())


def test_run_id_pattern_is_enforced() -> None:
    instance = _base_run()
    instance["run_id"] = "run_bad"
    with pytest.raises(ValidationError):
        validate(instance, _schema())


def test_invalid_status_is_rejected() -> None:
    instance = _base_run()
    instance["status"] = "published"
    with pytest.raises(ValidationError):
        validate(instance, _schema())


def test_unexpected_field_is_rejected() -> None:
    instance = _base_run()
    instance["wordpress_password"] = "must-not-exist"
    with pytest.raises(ValidationError):
        validate(instance, _schema())


def test_rejected_run_requires_rejected_human_review() -> None:
    instance = _base_run()
    instance["status"] = "rejected"
    instance["human_review"]["status"] = "rejected"
    validate(instance, _schema())


def test_failed_run_requires_delivery_error() -> None:
    instance = _base_run()
    instance["status"] = "failed"
    instance["delivery"]["status"] = "failed"
    instance["delivery"]["error"] = {"type": "TransportError", "message": "delivery failed"}
    validate(instance, _schema())
