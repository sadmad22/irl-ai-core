import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "shared" / "schemas" / "production-delivery-boundary.schema.json"


def _schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _delivery(status="ready"):
    delivery = {
        "delivery_id": "delivery_0123456789abcdef",
        "package_id": "package_0123456789abcdef",
        "publisher_id": "publisher_123",
        "adapter_id": "wordpress_adapter_v1",
        "target": "wordpress",
        "execution_mode": "live",
        "publication": {
            "mode": "wordpress_draft",
            "publish": False,
            "human_approval_required": True,
        },
        "request": {
            "title": "Example Insurance Guide",
            "content": "<h2>Overview</h2><p>Evidence-backed article text.</p><table><tr><td>Provider A</td></tr></table>",
            "status": "draft",
            "slug": "example-insurance-guide",
            "excerpt": "A concise insurance guide.",
            "media": [
                {
                    "image_id": "image_0",
                    "asset_ref": "media_artifact_0",
                    "alt_text": "Insurance coverage illustration",
                    "placement": "After overview",
                    "featured": True,
                }
            ],
            "links": [
                {
                    "link_id": "link_0",
                    "target_url": "https://insurancereviewlab.com/insurance/",
                    "anchor_text": "insurance coverage",
                    "placement": "Overview",
                    "kind": "internal",
                }
            ],
            "optimization": {
                "seo_title": "Example Insurance Guide",
                "meta_description": "Learn the essentials of example insurance.",
                "canonical_url": "https://insurancereviewlab.com/example-insurance-guide/",
            },
            "taxonomy": {"categories": ["Insurance"], "tags": ["Example"]},
        },
        "lifecycle_stage": "delivery_ready" if status == "ready" else "delivered_as_draft",
        "delivery_status": status,
        "audit": {
            "method": "production_delivery_boundary",
            "version": "v1",
            "validation_status": "validated",
        },
    }
    if status == "delivered":
        delivery["response"] = {
            "platform_post_id": 4957,
            "remote_status": "draft",
            "edit_url": "https://insurancereviewlab.com/wp-admin/post.php?post=4957&action=edit",
        }
    return delivery


def _validate(delivery):
    validator = Draft202012Validator(_schema(), format_checker=FormatChecker())
    return sorted(validator.iter_errors(delivery), key=lambda error: list(error.path))


def test_valid_ready_delivery_passes_schema():
    assert _validate(_delivery()) == []


def test_valid_delivered_draft_requires_and_accepts_platform_response():
    delivery = _delivery(status="delivered")
    assert _validate(delivery) == []
    assert delivery["response"]["remote_status"] == "draft"


def test_delivered_status_without_platform_response_fails():
    delivery = _delivery(status="delivered")
    delivery.pop("response")
    errors = _validate(delivery)
    assert errors
    assert any("response" in error.message for error in errors)


def test_failed_delivery_requires_error_details():
    delivery = _delivery(status="failed")
    delivery["lifecycle_stage"] = "delivery_ready"
    delivery["response"] = {"error_code": "WP_AUTH", "error_message": "Authentication failed"}
    assert _validate(delivery) == []


def test_failed_delivery_without_error_details_fails():
    delivery = _delivery(status="failed")
    delivery["lifecycle_stage"] = "delivery_ready"
    delivery["response"] = {}
    errors = _validate(delivery)
    assert errors
    assert any("error_code" in error.message or "error_message" in error.message for error in errors)


def test_request_is_draft_only():
    delivery = _delivery()
    delivery["request"]["status"] = "publish"
    errors = _validate(delivery)
    assert errors


def test_publication_intent_cannot_be_changed_at_delivery_boundary():
    delivery = _delivery()
    delivery["publication"]["publish"] = True
    errors = _validate(delivery)
    assert errors


def test_request_requires_media_links_optimization_and_taxonomy_domains():
    delivery = _delivery()
    for field in ("media", "links", "optimization", "taxonomy"):
        candidate = copy.deepcopy(delivery)
        candidate["request"].pop(field)
        assert _validate(candidate), field


def test_media_requires_materialized_asset_reference_and_alt_text():
    delivery = _delivery()
    delivery["request"]["media"][0].pop("asset_ref")
    errors = _validate(delivery)
    assert errors


def test_link_kind_is_explicit():
    delivery = _delivery()
    delivery["request"]["links"][0]["kind"] = "unknown"
    errors = _validate(delivery)
    assert errors


def test_unknown_request_fields_fail_closed():
    delivery = _delivery()
    delivery["request"]["invented_field"] = "must fail"
    errors = _validate(delivery)
    assert errors
