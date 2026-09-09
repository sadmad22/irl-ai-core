from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


def test_wordpress_connector_schema_is_valid():
    path = Path("shared/schemas/wordpress-connector.schema.json")
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_wordpress_connector_schema_rejects_publish():
    path = Path("shared/schemas/wordpress-connector.schema.json")
    schema = json.loads(path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    value = {
        "connector_id": "wpconn_0123456789abcdef",
        "schema_version": "1.0",
        "lifecycle_stage": "wordpress_connector_ready",
        "platform": "wordpress",
        "operation": "create_draft",
        "source": {"production_id": "production_0123456789abcdef"},
        "request_payload": {"title": "Test", "content": "<p>Body</p>", "status": "publish"},
        "response": {"delivery_status": "failed", "error": None},
        "audit": {"method": "wordpress_connector", "version": "v1", "validation_status": "validated"},
    }
    assert list(validator.iter_errors(value))
