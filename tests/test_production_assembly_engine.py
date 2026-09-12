from __future__ import annotations

import copy

import pytest

from agents.research.production_assembly_engine import (
    ProductionAssemblyEngineError,
    build_production_assembly,
)


def _inputs() -> dict:
    return {
        "article_draft": {
            "draft_id": "draft_123", "brief_id": "brief_123", "report_id": "report_123",
            "decision_id": "decision_123", "strategy_id": "strategy_123", "lifecycle_stage": "draft_ready",
            "content_type": "guide", "primary_keyword": "expat health insurance", "title": "Expat Health Insurance Guide",
            "slug": "expat-health-insurance-guide",
            "sections": [{
                "section_id": "section_0", "heading": "Overview", "body": "Evidence-backed article text.",
                "purpose": "Explain the topic", "evidence_refs": ["evidence_1"],
                "claims": [{"claim_id": "claim_1", "text": "Evidence-backed article text.", "evidence_refs": ["evidence_1"], "grounding_status": "grounded"}],
            }],
            "tables": [],
        },
        "quality": {"quality_id": "quality_123", "lifecycle_stage": "article_draft_quality_ready", "outcome": "passed", "audit": {"validation_status": "validated"}},
        "claim_audit": {"outcome": "passed", "audit": {"validation_status": "validated"}},
        "editorial_review": {"outcome": "approved", "audit": {"validation_status": "validated"}},
        "optimization": {"seo_title": "Expat Health Insurance Guide", "meta_description": "A practical guide to expat health insurance.", "canonical_url": "https://insurancereviewlab.com/expat-health-insurance/"},
        "media": {"images": [{"image_id": "image_1", "section_index": 0, "placement": "hero", "prompt": "Editorial insurance illustration", "alt_text": "Expat health insurance illustration", "materialization_status": "materialized", "asset_ref": "media_1"}]},
        "linking": {"internal": [{"link_id": "link_internal_1", "section_index": 0, "target_url": "https://insurancereviewlab.com/insurance/", "anchor_text": "insurance coverage", "placement": "body"}], "external": []},
        "taxonomy": {"categories": ["Expat Insurance"], "tags": ["health insurance"]},
        "production_intent": {"target": "wordpress", "mode": "wordpress_draft", "publish": False, "human_approval_required": True},
        "lineage": {"report_id": "report_123", "decision_id": "decision_123", "strategy_id": "strategy_123", "brief_id": "brief_123", "draft_id": "draft_123", "quality_id": "quality_123"},
    }


def test_builds_ready_assembly():
    result = build_production_assembly(project_name="expat-health-insurance", artifacts=_inputs())
    assert result["lifecycle_stage"] == "production_assembly_ready"
    assert result["audit"] == {"method": "production_assembly", "version": "v1", "validation_status": "validated"}
    assert result["artifacts"]["media"]["images"][0]["asset_ref"] == "media_1"


def test_assembly_id_is_deterministic():
    first = build_production_assembly(project_name="expat-health-insurance", artifacts=_inputs())
    second = build_production_assembly(project_name="expat-health-insurance", artifacts=_inputs())
    assert first["assembly_id"] == second["assembly_id"]


def test_different_project_changes_assembly_id():
    first = build_production_assembly(project_name="expat-health-insurance", artifacts=_inputs())
    second = build_production_assembly(project_name="consultant-liability", artifacts=_inputs())
    assert first["assembly_id"] != second["assembly_id"]


def test_does_not_mutate_inputs():
    source = _inputs()
    original = copy.deepcopy(source)
    build_production_assembly(project_name="expat-health-insurance", artifacts=source)
    assert source == original


@pytest.mark.parametrize(
    ("path", "code"),
    [
        (("taxonomy",), "INVALID_TAXONOMY"),
        (("production_intent", "publish"), "UNSAFE_PRODUCTION_INTENT"),
        (("quality", "outcome"), "QUALITY_GATE_FAILED"),
        (("claim_audit", "outcome"), "CLAIM_AUDIT_FAILED"),
        (("editorial_review", "outcome"), "EDITORIAL_GATE_FAILED"),
        (("media", "images", 0, "materialization_status"), "MEDIA_NOT_MATERIALIZED"),
        (("optimization", "seo_title"), "OPTIMIZATION_INCOMPLETE"),
    ],
)
def test_fail_closed_gates(path, code):
    source = _inputs()
    target = source
    for key in path[:-1]:
        target = target[key]
    key = path[-1]
    if path == ("taxonomy",):
        target[key]["categories"] = []
    elif path[-1] == "publish":
        target[key] = True
    elif path[-1] == "materialization_status":
        target[key] = "specified"
    else:
        target[key] = "failed"
    with pytest.raises(ProductionAssemblyEngineError, match=code):
        build_production_assembly(project_name="expat-health-insurance", artifacts=source)


def test_missing_artifact_is_rejected():
    source = _inputs()
    del source["linking"]
    with pytest.raises(ProductionAssemblyEngineError, match="MISSING_ARTIFACT"):
        build_production_assembly(project_name="expat-health-insurance", artifacts=source)


def test_missing_media_asset_ref_is_rejected():
    source = _inputs()
    del source["media"]["images"][0]["asset_ref"]
    with pytest.raises(ProductionAssemblyEngineError, match="INVALID_MEDIA"):
        build_production_assembly(project_name="expat-health-insurance", artifacts=source)


def test_invalid_lineage_is_rejected():
    source = _inputs()
    source["lineage"]["draft_id"] = "other_draft"
    with pytest.raises(ProductionAssemblyEngineError, match="LINEAGE_MISMATCH"):
        build_production_assembly(project_name="expat-health-insurance", artifacts=source)
