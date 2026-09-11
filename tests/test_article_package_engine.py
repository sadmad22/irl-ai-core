from __future__ import annotations

import copy

import pytest

from agents.research.article_package_engine import (
    ArticlePackageEngineError,
    build_article_package,
    validate_article_package,
)


def _artifacts(*, content_type: str = "guide") -> dict:
    draft = {
        "draft_id": "draft_123", "brief_id": "brief_123", "report_id": "report_123",
        "decision_id": "decision_123", "strategy_id": "strategy_123", "lifecycle_stage": "draft_ready",
        "content_type": content_type, "primary_keyword": "expat health insurance",
        "title": "Expat Health Insurance Guide", "slug": "expat-health-insurance-guide",
        "sections": [{
            "section_id": "section_0", "heading": "Overview", "body": "Expat health insurance provides international coverage.",
            "purpose": "Explain the topic", "evidence_refs": ["evidence_1"],
            "claims": [{"claim_id": "claim_1", "text": "Expat health insurance provides international coverage.", "evidence_refs": ["evidence_1"], "grounding_status": "grounded"}],
        }],
        "tables": ([{"table_id": "table_1", "title": "Coverage comparison", "section_index": 0,
                     "columns": ["Provider", "Coverage"], "rows": [["A", "International"]], "evidence_refs": ["evidence_1"]}]
                   if content_type == "comparison" else []),
    }
    quality = {"quality_id": "quality_123", "draft_id": "draft_123", "brief_id": "brief_123", "report_id": "report_123",
               "decision_id": "decision_123", "strategy_id": "strategy_123", "lifecycle_stage": "article_draft_quality_ready",
               "outcome": "passed", "audit": {"validation_status": "validated"}}
    return {
        "article_draft": draft, "quality": quality,
        "claim_audit": {"outcome": "passed", "audit": {"validation_status": "validated"}},
        "editorial_review": {"outcome": "approved", "audit": {"validation_status": "validated"}},
        "optimization": {"seo_title": "Expat Health Insurance Guide", "meta_description": "A practical guide to expat health insurance."},
        "media": {"images": [{"image_id": "image_1", "section_index": 0, "placement": "after_intro", "prompt": "Editorial illustration", "alt_text": "Expat health insurance illustration", "materialization_status": "materialized", "asset_ref": "media_1"}]},
        "linking": {"internal": [], "external": []},
        "taxonomy": {"categories": ["Expat Insurance"], "tags": ["health insurance"]},
        "production_intent": {"target": "wordpress", "mode": "wordpress_draft", "publish": False, "human_approval_required": True},
        "lineage": {"report_id": "report_123", "decision_id": "decision_123", "strategy_id": "strategy_123", "brief_id": "brief_123", "draft_id": "draft_123", "quality_id": "quality_123"},
    }


def test_build_delivery_ready_package():
    package = build_article_package(project_name="expat-health-insurance", artifacts=_artifacts())
    assert package["identity"]["lifecycle_stage"] == "delivery_ready"
    assert package["identity"]["package_id"].startswith("package_")
    assert package["delivery"]["publish"] is False
    assert package["media"]["images"][0]["asset_ref"] == "media_1"
    assert package["audit"]["validation_status"] == "validated"


def test_package_id_is_deterministic_and_input_is_not_mutated():
    artifacts = _artifacts()
    original = copy.deepcopy(artifacts)
    first = build_article_package(project_name="expat-health-insurance", artifacts=artifacts)
    second = build_article_package(project_name="expat-health-insurance", artifacts=artifacts)
    assert first["identity"]["package_id"] == second["identity"]["package_id"]
    assert artifacts == original


def test_missing_upstream_artifact_fails_closed():
    artifacts = _artifacts(); del artifacts["taxonomy"]
    with pytest.raises(ArticlePackageEngineError) as exc:
        build_article_package(project_name="expat-health-insurance", artifacts=artifacts)
    assert exc.value.code == "MISSING_ARTIFACT"
    assert "taxonomy" in exc.value.details


def test_upstream_quality_must_pass():
    artifacts = _artifacts(); artifacts["quality"]["outcome"] = "needs_revision"
    with pytest.raises(ArticlePackageEngineError) as exc:
        build_article_package(project_name="expat-health-insurance", artifacts=artifacts)
    assert exc.value.code == "UPSTREAM_NOT_READY"


def test_lineage_mismatch_fails_closed():
    artifacts = _artifacts(); artifacts["lineage"]["draft_id"] = "draft_other"
    with pytest.raises(ArticlePackageEngineError) as exc:
        build_article_package(project_name="expat-health-insurance", artifacts=artifacts)
    assert exc.value.code == "LINEAGE_MISMATCH"


def test_unsafe_publication_intent_is_rejected():
    artifacts = _artifacts(); artifacts["production_intent"]["publish"] = True
    with pytest.raises(ArticlePackageEngineError) as exc:
        build_article_package(project_name="expat-health-insurance", artifacts=artifacts)
    assert exc.value.code == "UNSAFE_PUBLICATION_INTENT"


def test_unmaterialized_media_cannot_reach_delivery_ready():
    artifacts = _artifacts(); artifacts["media"]["images"][0]["materialization_status"] = "specified"
    artifacts["media"]["images"][0].pop("asset_ref")
    with pytest.raises(ArticlePackageEngineError) as exc:
        build_article_package(project_name="expat-health-insurance", artifacts=artifacts)
    assert exc.value.code == "PACKAGE_INVALID"


def test_comparison_requires_table():
    artifacts = _artifacts(content_type="comparison"); artifacts["article_draft"]["tables"] = []
    with pytest.raises(ArticlePackageEngineError) as exc:
        build_article_package(project_name="expat-health-insurance", artifacts=artifacts)
    assert exc.value.code == "REQUIRED_ASSET_MISSING"


def test_package_validation_returns_deep_copy_and_validated_stage():
    package = build_article_package(project_name="expat-health-insurance", artifacts=_artifacts(), target_stage="package_assembled")
    original = copy.deepcopy(package)
    validated = validate_article_package(package=package, target_stage="package_validated")
    assert validated["identity"]["lifecycle_stage"] == "package_validated"
    assert validated["audit"]["validation_status"] == "validated"
    assert package == original


def test_delivery_ready_validation_rejects_ungrounded_claim():
    package = build_article_package(project_name="expat-health-insurance", artifacts=_artifacts(), target_stage="package_assembled")
    package["content"]["claims"][0]["grounding_status"] = "blocked"
    with pytest.raises(ArticlePackageEngineError) as exc:
        validate_article_package(package=package, target_stage="delivery_ready")
    assert exc.value.code == "PACKAGE_INVALID"
    assert any("claim claim_1" in detail for detail in exc.value.details)


def test_delivery_ready_validation_rejects_unmaterialized_image():
    package = build_article_package(project_name="expat-health-insurance", artifacts=_artifacts(), target_stage="package_assembled")
    package["media"]["images"][0]["materialization_status"] = "specified"
    package["media"]["images"][0].pop("asset_ref")
    with pytest.raises(ArticlePackageEngineError) as exc:
        validate_article_package(package=package, target_stage="delivery_ready")
    assert exc.value.code == "PACKAGE_INVALID"
    assert any("image image_1" in detail for detail in exc.value.details)
