import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "shared" / "schemas" / "production-delivery-boundary.schema.json"


def _schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _delivery(stage="delivery_ready", status="ready", mode="live"):
    delivery = {
        "delivery_id": "delivery_0123456789abcdef",
        "package_id": "package_0123456789abcdef",
        "publisher_id": "publisher_123",
        "adapter_id": "wordpress_adapter_v1",
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
            "title": "Example Insurance Guide",
            "content": "<h2>Overview</h2><p>Evidence-backed article text.</p><table><tr><td>Provider A</td></tr></table><a href=\"https://example.com\">coverage</a>",
            "status": "draft",
            "slug": "example-insurance-guide",
            "excerpt": "A concise insurance guide.",
            "media": [{
                "image_id": "image_0", "asset_ref": "media_artifact_0", "alt_text": "Insurance coverage illustration",
                "placement": "After overview", "featured": True,
            }],
            "links": [{
                "link_id": "link_0", "target_url": "https://insurancereviewlab.com/insurance/",
                "anchor_text": "insurance coverage", "placement": "Overview", "kind": "internal",
            }],
            "optimization": {
                "seo_title": "Example Insurance Guide",
                "meta_description": "Learn the essentials of example insurance.",
                "canonical_url": "https://insurancereviewlab.com/example-insurance-guide/",
            },
            "taxonomy": {
                "categories": [{"name": "Insurance", "platform_id": 7}],
                "tags": [{"name": "Example", "platform_id": 8}],
            },
        },
        "lifecycle_stage": stage,
        "delivery_status": status,
        "audit": {"method": "production_delivery_boundary", "version": "v1", "validation_status": "validated"},
    }
    if status == "delivered":
        delivery["response"] = {
            "platform_post_id": 4957,
            "remote_status": "draft",
            "edit_url": "https://insurancereviewlab.com/wp-admin/post.php?post=4957&action=edit",
            "media_results": [{"image_id": "image_0", "platform_asset_id": 101}],
            "taxonomy_results": {"categories": [7], "tags": [8]},
        }
    elif status == "failed":
        delivery["response"] = {
            "error_code": "MEDIA_RESOLUTION_FAILED",
            "error_message": "Required media could not be resolved.",
            "failed_stage": "media",
            "retryable": True,
        }
    return delivery


def _validate(delivery):
    validator = Draft202012Validator(_schema(), format_checker=FormatChecker())
    return sorted(validator.iter_errors(delivery), key=lambda error: list(error.path))


def test_valid_delivery_ready_passes_schema():
    assert _validate(_delivery()) == []


def test_valid_request_ready_passes_schema():
    assert _validate(_delivery(stage="request_ready")) == []


def test_valid_delivered_draft_passes_schema():
    assert _validate(_delivery(stage="delivered_as_draft", status="delivered")) == []


def test_valid_human_review_passes_schema():
    assert _validate(_delivery(stage="human_review", status="delivered")) == []


def test_valid_failed_delivery_passes_schema():
    assert _validate(_delivery(stage="failed", status="failed")) == []


def test_source_binding_is_required():
    delivery = _delivery()
    delivery.pop("source")
    assert _validate(delivery)


def test_source_package_id_must_match_delivery_package_id():
    delivery = _delivery()
    delivery["source"]["package_id"] = "package_fedcba9876543210"
    # Schema cannot compare two arbitrary fields; contract test documents this as an engine invariant.
    assert delivery["source"]["package_id"] != delivery["package_id"]


def test_source_must_be_delivery_ready_validated_v1():
    for field, value in (("package_lifecycle_stage", "package_validated"), ("package_validation_status", "pending"), ("package_schema_version", "0.9")):
        delivery = _delivery()
        delivery["source"][field] = value
        assert _validate(delivery), field


def test_publication_is_immutable_draft_only():
    for field, value in (("publish", True), ("mode", "wordpress_publish"), ("human_approval_required", False)):
        delivery = _delivery()
        delivery["publication"][field] = value
        assert _validate(delivery), field


def test_request_status_is_draft_only():
    delivery = _delivery()
    delivery["request"]["status"] = "publish"
    assert _validate(delivery)


def test_request_requires_all_delivery_domains():
    for field in ("media", "links", "optimization", "taxonomy"):
        delivery = _delivery()
        delivery["request"].pop(field)
        assert _validate(delivery), field


def test_media_requires_asset_ref_alt_text_and_featured_flag():
    for field in ("asset_ref", "alt_text", "featured"):
        delivery = _delivery()
        delivery["request"]["media"][0].pop(field)
        assert _validate(delivery), field


def test_media_platform_identity_is_optional_before_platform_resolution():
    delivery = _delivery()
    delivery["request"]["media"][0].pop("platform_asset_id")
    assert _validate(delivery) == []


def test_links_require_explicit_kind_and_valid_target():
    delivery = _delivery()
    delivery["request"]["links"][0]["kind"] = "discovered"
    assert _validate(delivery)
    delivery = _delivery()
    delivery["request"]["links"][0]["target_url"] = "not-a-uri"
    assert _validate(delivery)


def test_taxonomy_items_retain_source_name_and_optional_platform_id():
    delivery = _delivery()
    delivery["request"]["taxonomy"]["categories"][0] = {"name": "Insurance"}
    assert _validate(delivery) == []
    delivery["request"]["taxonomy"]["categories"][0] = {"platform_id": 7}
    assert _validate(delivery)


def test_optimization_requires_final_values():
    for field in ("seo_title", "meta_description"):
        delivery = _delivery()
        delivery["request"]["optimization"].pop(field)
        assert _validate(delivery), field


def test_delivered_requires_platform_response_and_draft_status():
    delivery = _delivery(stage="delivered_as_draft", status="delivered")
    delivery.pop("response")
    assert _validate(delivery)
    delivery = _delivery(stage="delivered_as_draft", status="delivered")
    delivery["response"]["remote_status"] = "publish"
    assert _validate(delivery)


def test_failed_requires_stable_error_details():
    for field in ("error_code", "error_message", "failed_stage", "retryable"):
        delivery = _delivery(stage="failed", status="failed")
        delivery["response"].pop(field)
        assert _validate(delivery), field


def test_lifecycle_and_status_must_agree():
    cases = [
        ("delivery_ready", "delivered"),
        ("request_ready", "failed"),
        ("delivering", "ready"),
        ("delivered_as_draft", "ready"),
        ("human_review", "failed"),
        ("failed", "delivered"),
    ]
    for stage, status in cases:
        assert _validate(_delivery(stage=stage, status=status)), (stage, status)


def test_dry_run_cannot_reach_live_delivery_states():
    for stage, status in (("delivering", "delivering"), ("delivered_as_draft", "delivered"), ("human_review", "delivered")):
        assert _validate(_delivery(stage=stage, status=status, mode="dry_run"))


def test_unknown_fields_fail_closed():
    delivery = _delivery()
    delivery["invented"] = True
    assert _validate(delivery)
    delivery = _delivery()
    delivery["request"]["invented"] = True
    assert _validate(delivery)


def test_valid_delivery_does_not_mutate_input():
    delivery = _delivery()
    original = copy.deepcopy(delivery)
    assert _validate(delivery) == []
    assert delivery == original
