from __future__ import annotations

import json

import pytest

from agents.research.wordpress_connector import (
    build_wordpress_connector_request,
    deliver_wordpress_draft_from_production,
)
from agents.research.wordpress_draft_delivery_client import WordPressConnection


def production():
    return {
        "production_id": "production_0123456789abcdef",
        "lifecycle_stage": "production_ready",
        "publication": {
            "mode": "wordpress_draft",
            "publish": False,
            "human_approval_required": True,
        },
        "article": {
            "title": "Consultant Insurance Coverage",
            "sections": [
                {"heading": "What You Need to Know", "body": "<p>Coverage matters.</p>"},
                {"heading": "Cost", "body": "<p>Compare limits and deductibles.</p>"},
            ],
        },
    }


def connection():
    return WordPressConnection("https://example.com", "editor", "app-password")


class Response:
    def __init__(self, data):
        self.data = data

    def read(self):
        return json.dumps(self.data).encode("utf-8")


def test_builds_connector_request_from_production():
    result = build_wordpress_connector_request(production())

    assert result["schema_version"] == "1.0"
    assert result["lifecycle_stage"] == "wordpress_connector_ready"
    assert result["platform"] == "wordpress"
    assert result["operation"] == "create_draft"
    assert result["source"]["production_id"] == "production_0123456789abcdef"
    assert result["request_payload"]["status"] == "draft"
    assert "<h2>What You Need to Know</h2>" in result["request_payload"]["content"]


def test_escapes_section_heading_markup():
    value = production()
    value["article"]["sections"][0]["heading"] = "<script>alert(1)</script>"
    result = build_wordpress_connector_request(value)
    assert "<script>" not in result["request_payload"]["content"]
    assert "&lt;script&gt;" in result["request_payload"]["content"]


def test_rejects_invalid_production_id():
    value = production()
    value["production_id"] = "production_invalid"
    with pytest.raises(ValueError, match="production_id"):
        build_wordpress_connector_request(value)


def test_connector_id_is_deterministic():
    first = build_wordpress_connector_request(production())
    second = build_wordpress_connector_request(production())
    assert first["connector_id"] == second["connector_id"]


@pytest.mark.parametrize(
    "mutator, message",
    [
        (lambda p: p.update(lifecycle_stage="running"), "production_ready"),
        (lambda p: p["publication"].update(mode="wordpress_publish"), "wordpress_draft"),
        (lambda p: p["publication"].update(publish=True), "publish=false"),
        (lambda p: p["publication"].update(human_approval_required=False), "human approval"),
    ],
)
def test_rejects_invalid_production_boundary(mutator, message):
    value = production()
    mutator(value)
    with pytest.raises(ValueError, match=message):
        build_wordpress_connector_request(value)


def test_delivers_as_draft_only():
    seen = {}

    def transport(request, timeout):
        seen["method"] = request.method
        seen["body"] = json.loads(request.data)
        return Response({"id": 321, "status": "draft", "link": "https://example.com/?p=321"})

    result = deliver_wordpress_draft_from_production(
        production(), connection=connection(), transport=transport
    )

    assert result["response"]["delivery_status"] == "delivered"
    assert result["response"]["post_id"] == 321
    assert result["response"]["remote_status"] == "draft"
    assert result["response"]["edit_url"] == "https://example.com/wp-admin/post.php?post=321&action=edit"
    assert seen["method"] == "POST"
    assert seen["body"]["status"] == "draft"
    assert "publish" not in seen["body"] or seen["body"]["publish"] is not True


def test_rejects_non_draft_remote_response():
    def transport(request, timeout):
        return Response({"id": 321, "status": "publish"})

    with pytest.raises(RuntimeError, match="immutable draft"):
        deliver_wordpress_draft_from_production(
            production(), connection=connection(), transport=transport
        )


def test_missing_remote_post_id_fails():
    def transport(request, timeout):
        return Response({"status": "draft"})

    with pytest.raises(RuntimeError, match="post id"):
        deliver_wordpress_draft_from_production(
            production(), connection=connection(), transport=transport
        )


def test_connector_does_not_contain_credentials():
    result = build_wordpress_connector_request(production())
    text = json.dumps(result)
    assert "editor" not in text
    assert "app-password" not in text
    assert "WORDPRESS_APPLICATION_PASSWORD" not in text
