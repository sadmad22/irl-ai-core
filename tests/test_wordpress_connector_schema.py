from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


def schema():
    return json.loads(Path("shared/schemas/wordpress-connector.schema.json").read_text(encoding="utf-8"))


def base_value():
    return {
        "connector_id": "wpconn_0123456789abcdef",
        "schema_version": "1.0",
        "lifecycle_stage": "wordpress_connector_ready",
        "platform": "wordpress",
        "operation": "create_draft",
        "source": {"production_id": "production_0123456789abcdef"},
        "request_payload": {"title": "Test", "content": "<p>Body</p>", "status": "draft"},
        "response": {"delivery_status": "delivered", "post_id": 123, "remote_status": "draft", "error": None},
        "audit": {"method": "wordpress_connector", "version": "v1", "validation_status": "validated"},
    }


def test_wordpress_connector_schema_is_valid():
    Draft202012Validator.check_schema(schema())


def test_wordpress_connector_schema_accepts_valid_delivered_record():
    assert list(Draft202012Validator(schema()).iter_errors(base_value())) == []


def test_wordpress_connector_schema_rejects_publish():
    value = base_value()
    value["request_payload"]["status"] = "publish"
    assert list(Draft202012Validator(schema()).iter_errors(value))


def test_wordpress_connector_schema_rejects_delivered_without_post_id():
    value = base_value()
    del value["response"]["post_id"]
    assert list(Draft202012Validator(schema()).iter_errors(value))


def test_wordpress_connector_schema_rejects_failed_without_error():
    value = base_value()
    value["response"] = {"delivery_status": "failed"}
    assert list(Draft202012Validator(schema()).iter_errors(value))
