from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

from agents.research.wordpress_delivery_adapter import (
    WordPressDeliveryAdapterError,
    build_wordpress_delivery_request,
    deliver_wordpress_delivery_boundary,
)


def _boundary(*, mode="dry_run"):
    media = {
        "image_id": "image_1",
        "asset_ref": "https://cdn.example.com/image-1.jpg",
        "alt_text": "Expat health insurance illustration",
        "placement": "after_intro",
        "featured": True,
    }
    return {
        "delivery_id": "delivery_0123456789abcdef",
        "package_id": "package_0123456789abcdef",
        "publisher_id": "publisher_123",
        "adapter_id": "boundary_adapter_v1",
        "target": "wordpress",
        "execution_mode": mode,
        "publication": {"mode": "wordpress_draft", "publish": False, "human_approval_required": True},
        "source": {
            "package_id": "package_0123456789abcdef",
            "package_lifecycle_stage": "delivery_ready",
            "package_validation_status": "validated",
            "package_schema_version": "1.0",
        },
        "request": {
            "title": "Expat Health Insurance Guide",
            "content": '<h2>Overview</h2><p>Evidence-backed article text.</p><img src="https://cdn.example.com/image-1.jpg" alt="Expat health insurance illustration" />',
            "status": "draft",
            "slug": "expat-health-insurance-guide",
            "excerpt": "A practical guide.",
            "media": [media],
            "links": [{
                "link_id": "link_1",
                "target_url": "https://insurancereviewlab.com/insurance/",
                "anchor_text": "insurance coverage",
                "placement": "Overview",
                "kind": "internal",
            }],
            "optimization": {
                "seo_title": "Expat Health Insurance Guide",
                "meta_description": "A practical guide to expat health insurance.",
            },
            "taxonomy": {"categories": [{"name": "Expat Insurance"}], "tags": [{"name": "health insurance"}]},
        },
        "lifecycle_stage": "delivery_ready",
        "delivery_status": "ready",
        "audit": {"method": "production_delivery_boundary", "version": "v1", "validation_status": "validated"},
    }


def test_dry_run_consumes_boundary_and_builds_request_without_network():
    boundary = _boundary()
    original = copy.deepcopy(boundary)
    result = build_wordpress_delivery_request(boundary=boundary)
    assert result["lifecycle_stage"] == "request_ready"
    assert result["request_payload"]["status"] == "draft"
    assert result["request_payload"]["slug"] == "expat-health-insurance-guide"
    assert result["request_payload"]["content"] == boundary["request"]["content"]
    assert result["media"][0]["asset_ref"] == "https://cdn.example.com/image-1.jpg"
    assert result["links"][0]["target_url"] == boundary["request"]["links"][0]["target_url"]
    assert boundary == original


def test_dry_run_never_invents_or_sends_publish_status():
    result = build_wordpress_delivery_request(boundary=_boundary())
    assert result["request_payload"]["status"] == "draft"
    assert "publish" not in result["request_payload"]


def test_live_requires_resolved_category_and_featured_media():
    with pytest.raises(WordPressDeliveryAdapterError) as exc:
        build_wordpress_delivery_request(
            boundary=_boundary(mode="live"),
            seo_meta_keys={"seo_title": "seo_title", "meta_description": "meta_description"},
        )
    assert exc.value.code == "MEDIA_NOT_RESOLVED"

    boundary = _boundary(mode="live")
    boundary["request"]["taxonomy"]["categories"][0]["platform_id"] = 7
    boundary["request"]["taxonomy"]["tags"][0]["platform_id"] = 9
    boundary["request"]["media"][0]["platform_asset_id"] = 101
    result = build_wordpress_delivery_request(
        boundary=boundary,
        seo_meta_keys={"seo_title": "seo_title", "meta_description": "meta_description"},
    )
    assert result["request_payload"]["categories"] == [7]
    assert result["request_payload"]["tags"] == [9]
    assert result["request_payload"]["featured_media"] == 101
    assert result["request_payload"]["meta"] == {
        "seo_title": "Expat Health Insurance Guide",
        "meta_description": "A practical guide to expat health insurance.",
    }


def test_live_requires_explicit_seo_mapping():
    boundary = _boundary(mode="live")
    boundary["request"]["taxonomy"]["categories"][0]["platform_id"] = 7
    boundary["request"]["taxonomy"]["tags"][0]["platform_id"] = 9
    boundary["request"]["media"][0]["platform_asset_id"] = 101
    with pytest.raises(WordPressDeliveryAdapterError) as exc:
        build_wordpress_delivery_request(boundary=boundary)
    assert exc.value.code == "SEO_METADATA_UNSUPPORTED"


def test_live_delivery_uses_client_and_returns_human_review():
    boundary = _boundary(mode="live")
    boundary["request"]["taxonomy"]["categories"][0]["platform_id"] = 7
    boundary["request"]["taxonomy"]["tags"][0]["platform_id"] = 9
    boundary["request"]["media"][0]["platform_asset_id"] = 101

    captured = {}

    def fake_transport(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return SimpleNamespace(content=json.dumps({"id": 4957, "status": "draft"}).encode("utf-8"))

    from agents.research.wordpress_draft_delivery_client import WordPressConnection

    result = deliver_wordpress_delivery_boundary(
        boundary=boundary,
        connection=WordPressConnection(
            base_url="https://insurancereviewlab.com",
            username="test-user",
            application_password="not-real",
        ),
        transport=fake_transport,
        seo_meta_keys={"seo_title": "seo_title", "meta_description": "meta_description"},
    )
    assert result["lifecycle_stage"] == "human_review"
    assert result["delivery_status"] == "delivered"
    assert result["response"]["platform_post_id"] == 4957
    assert result["response"]["remote_status"] == "draft"
    assert captured["payload"]["status"] == "draft"
    assert captured["payload"]["featured_media"] == 101
    assert captured["payload"]["categories"] == [7]
    assert captured["payload"]["tags"] == [9]
    assert "seo_title" in captured["payload"]["meta"]


def test_remote_publish_response_is_rejected_by_existing_client():
    boundary = _boundary(mode="live")
    boundary["request"]["taxonomy"]["categories"][0]["platform_id"] = 7
    boundary["request"]["taxonomy"]["tags"][0]["platform_id"] = 9
    boundary["request"]["media"][0]["platform_asset_id"] = 101

    def fake_transport(request, timeout):
        return SimpleNamespace(content=json.dumps({"id": 4957, "status": "publish"}).encode("utf-8"))

    from agents.research.wordpress_draft_delivery_client import WordPressConnection

    with pytest.raises(RuntimeError, match="immutable draft requirement"):
        deliver_wordpress_delivery_boundary(
            boundary=boundary,
            connection=WordPressConnection(
                base_url="https://insurancereviewlab.com",
                username="test-user",
                application_password="not-real",
            ),
            transport=fake_transport,
            seo_meta_keys={"seo_title": "seo_title", "meta_description": "meta_description"},
        )
