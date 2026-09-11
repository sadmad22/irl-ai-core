from __future__ import annotations

import copy

import pytest

from agents.research.production_delivery_boundary_engine import (
    ProductionDeliveryBoundaryEngineError,
    build_production_delivery_boundary,
    validate_production_delivery_boundary,
)


def _package(*, lifecycle="delivery_ready", validation="validated", content_type="guide"):
    table = {"table_id": "table_1", "title": "Comparison", "section_id": "section_0", "columns": ["Provider", "Coverage"], "rows": [["A", "International"]], "evidence_refs": ["evidence_1"]}
    return {
        "identity": {"package_id": "package_0123456789abcdef", "project_name": "expat-health-insurance", "schema_version": "1.0", "lifecycle_stage": lifecycle, "content_type": content_type, "primary_keyword": "expat health insurance"},
        "lineage": {"report_id": "report_123", "decision_id": "decision_123", "strategy_id": "strategy_123", "brief_id": "brief_123", "draft_id": "draft_123", "quality_id": "quality_123"},
        "content": {
            "article": {"title": "Expat Health Insurance Guide", "slug": "expat-health-insurance-guide", "excerpt": "A practical guide."},
            "sections": [{"section_id": "section_0", "order": 0, "heading": "Overview", "body": "Evidence-backed article text.", "purpose": "Explain the topic", "claim_ids": ["claim_1"], "evidence_refs": ["evidence_1"]}],
            "claims": [{"claim_id": "claim_1", "section_id": "section_0", "text": "Evidence-backed article text.", "evidence_refs": ["evidence_1"], "grounding_status": "grounded"}],
            "tables": [table] if content_type == "comparison" else [],
        },
        "media": {"images": [{"image_id": "image_1", "section_id": "section_0", "placement": "after_intro", "prompt": "Editorial illustration", "alt_text": "Expat health insurance illustration", "materialization_status": "materialized", "asset_ref": "media_1"}], "featured_image": {"image_id": "image_1"}},
        "linking": {"internal": [{"link_id": "link_1", "section_id": "section_0", "target_url": "https://insurancereviewlab.com/insurance/", "anchor_text": "insurance coverage", "placement": "Overview"}], "external": []},
        "optimization": {"seo_title": "Expat Health Insurance Guide", "meta_description": "A practical guide to expat health insurance."},
        "taxonomy": {"categories": ["Expat Insurance"], "tags": ["health insurance"]},
        "delivery": {"target": "wordpress", "mode": "wordpress_draft", "publish": False, "human_approval_required": True},
        "audit": {"method": "article_package_contract", "version": "v1", "validation_status": validation},
    }


def test_builds_deterministic_draft_only_boundary():
    package = _package()
    first = build_production_delivery_boundary(package=package, publisher_id="publisher_123", adapter_id="wordpress_adapter_v1")
    second = build_production_delivery_boundary(package=package, publisher_id="publisher_123", adapter_id="wordpress_adapter_v1")
    assert first["delivery_id"] == second["delivery_id"]
    assert first["lifecycle_stage"] == "delivery_ready"
    assert first["delivery_status"] == "ready"
    assert first["publication"] == {"mode": "wordpress_draft", "publish": False, "human_approval_required": True}
    assert first["request"]["status"] == "draft"


def test_different_adapter_changes_delivery_identity():
    package = _package()
    first = build_production_delivery_boundary(package=package, publisher_id="publisher_123", adapter_id="wordpress_adapter_v1")
    second = build_production_delivery_boundary(package=package, publisher_id="publisher_123", adapter_id="wordpress_adapter_v2")
    assert first["delivery_id"] != second["delivery_id"]


def test_input_package_is_not_mutated():
    package = _package()
    original = copy.deepcopy(package)
    build_production_delivery_boundary(package=package, publisher_id="publisher_123", adapter_id="wordpress_adapter_v1")
    assert package == original


@pytest.mark.parametrize("lifecycle", ["package_assembled", "package_validated", "production_ready"])
def test_non_delivery_ready_package_fails_closed(lifecycle):
    with pytest.raises(ProductionDeliveryBoundaryEngineError) as exc:
        build_production_delivery_boundary(package=_package(lifecycle=lifecycle), publisher_id="publisher_123", adapter_id="wordpress_adapter_v1")
    assert exc.value.code == "SOURCE_NOT_READY"


def test_unvalidated_package_fails_closed():
    with pytest.raises(ProductionDeliveryBoundaryEngineError) as exc:
        build_production_delivery_boundary(package=_package(validation="pending"), publisher_id="publisher_123", adapter_id="wordpress_adapter_v1")
    assert exc.value.code == "SOURCE_NOT_READY"


def test_unsafe_package_publication_intent_is_rejected():
    package = _package()
    package["delivery"]["publish"] = True
    with pytest.raises(ProductionDeliveryBoundaryEngineError) as exc:
        build_production_delivery_boundary(package=package, publisher_id="publisher_123", adapter_id="wordpress_adapter_v1")
    assert exc.value.code == "SOURCE_NOT_READY"


def test_missing_materialized_media_fails_closed():
    package = _package()
    package["media"]["images"][0]["materialization_status"] = "specified"
    package["media"]["images"][0].pop("asset_ref")
    with pytest.raises(ProductionDeliveryBoundaryEngineError) as exc:
        build_production_delivery_boundary(package=package, publisher_id="publisher_123", adapter_id="wordpress_adapter_v1")
    assert exc.value.code == "MEDIA_NOT_MATERIALIZED"


def test_ungrounded_claim_fails_closed():
    package = _package()
    package["content"]["claims"][0]["grounding_status"] = "blocked"
    with pytest.raises(ProductionDeliveryBoundaryEngineError) as exc:
        build_production_delivery_boundary(package=package, publisher_id="publisher_123", adapter_id="wordpress_adapter_v1")
    assert exc.value.code == "UPSTREAM_NOT_READY"


def test_comparison_without_table_fails_closed():
    package = _package(content_type="comparison")
    package["content"]["tables"] = []
    with pytest.raises(ProductionDeliveryBoundaryEngineError) as exc:
        build_production_delivery_boundary(package=package, publisher_id="publisher_123", adapter_id="wordpress_adapter_v1")
    assert exc.value.code == "REQUIRED_ASSET_MISSING"


def test_tables_links_media_seo_and_taxonomy_are_preserved():
    package = _package(content_type="comparison")
    boundary = build_production_delivery_boundary(package=package, publisher_id="publisher_123", adapter_id="wordpress_adapter_v1")
    request = boundary["request"]
    assert request["title"] == package["content"]["article"]["title"]
    assert request["slug"] == package["content"]["article"]["slug"]
    assert request["media"][0]["asset_ref"] == "media_1"
    assert request["media"][0]["alt_text"] == "Expat health insurance illustration"
    assert request["links"][0]["target_url"] == "https://insurancereviewlab.com/insurance/"
    assert request["links"][0]["kind"] == "internal"
    assert request["optimization"]["seo_title"] == package["optimization"]["seo_title"]
    assert request["taxonomy"]["categories"][0]["name"] == "Expat Insurance"
    assert "<table>" in request["content"]
    assert "media_1" in request["content"]


def test_invalid_explicit_link_fails_closed():
    package = _package()
    package["linking"]["internal"][0]["target_url"] = "not-a-uri"
    with pytest.raises(ProductionDeliveryBoundaryEngineError) as exc:
        build_production_delivery_boundary(package=package, publisher_id="publisher_123", adapter_id="wordpress_adapter_v1")
    assert exc.value.code == "INVALID_LINKS"


def test_boundary_validator_returns_deep_copy_and_rejects_source_mismatch():
    boundary = build_production_delivery_boundary(package=_package(), publisher_id="publisher_123", adapter_id="wordpress_adapter_v1")
    original = copy.deepcopy(boundary)
    validated = validate_production_delivery_boundary(boundary)
    assert validated == original
    broken = copy.deepcopy(boundary)
    broken["source"]["package_id"] = "package_fedcba9876543210"
    with pytest.raises(ProductionDeliveryBoundaryEngineError) as exc:
        validate_production_delivery_boundary(broken)
    assert exc.value.code == "BOUNDARY_INVALID"


def test_dry_run_never_enters_live_delivery_states():
    boundary = build_production_delivery_boundary(package=_package(), publisher_id="publisher_123", adapter_id="wordpress_adapter_v1", execution_mode="dry_run")
    assert boundary["execution_mode"] == "dry_run"
    assert boundary["lifecycle_stage"] == "delivery_ready"
    assert boundary["delivery_status"] == "ready"


def test_invalid_execution_mode_and_missing_identity_fail_closed():
    with pytest.raises(ProductionDeliveryBoundaryEngineError) as exc:
        build_production_delivery_boundary(package=_package(), publisher_id="", adapter_id="wordpress_adapter_v1")
    assert exc.value.code == "INVALID_INPUT"
    with pytest.raises(ProductionDeliveryBoundaryEngineError) as exc:
        build_production_delivery_boundary(package=_package(), publisher_id="publisher_123", adapter_id="wordpress_adapter_v1", execution_mode="publish")
    assert exc.value.code == "INVALID_INPUT"
