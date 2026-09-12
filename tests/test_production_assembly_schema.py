from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "shared" / "schemas" / "production-assembly.schema.json"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assembly(*, stage: str = "production_assembly_ready") -> dict:
    return {
        "assembly_id": "assembly_0123456789abcdef",
        "project_name": "expat-health-insurance",
        "schema_version": "1.0",
        "lifecycle_stage": stage,
        "lineage": {
            "report_id": "report_123",
            "decision_id": "decision_123",
            "strategy_id": "strategy_123",
            "brief_id": "brief_123",
            "draft_id": "draft_123",
            "quality_id": "quality_123",
        },
        "artifacts": {
            "article_draft": {
                "draft_id": "draft_123",
                "brief_id": "brief_123",
                "report_id": "report_123",
                "decision_id": "decision_123",
                "strategy_id": "strategy_123",
                "lifecycle_stage": "draft_ready",
                "content_type": "guide",
                "primary_keyword": "expat health insurance",
                "title": "Expat Health Insurance Guide",
                "slug": "expat-health-insurance-guide",
                "sections": [{
                    "section_id": "section_0",
                    "heading": "Overview",
                    "body": "Evidence-backed article text.",
                    "purpose": "Explain the topic",
                    "evidence_refs": ["evidence_1"],
                    "claims": [{
                        "claim_id": "claim_1",
                        "text": "Evidence-backed article text.",
                        "evidence_refs": ["evidence_1"],
                        "grounding_status": "grounded",
                    }],
                }],
                "tables": [],
            },
            "quality": {
                "quality_id": "quality_123",
                "lifecycle_stage": "article_draft_quality_ready",
                "outcome": "passed",
                "audit": {"validation_status": "validated"},
            },
            "claim_audit": {"outcome": "passed", "audit": {"validation_status": "validated"}},
            "editorial_review": {"outcome": "approved", "audit": {"validation_status": "validated"}},
            "optimization": {
                "seo_title": "Expat Health Insurance Guide",
                "meta_description": "A practical guide to expat health insurance.",
                "canonical_url": "https://insurancereviewlab.com/expat-health-insurance/",
            },
            "media": {
                "images": [{
                    "image_id": "image_1",
                    "section_index": 0,
                    "placement": "hero",
                    "prompt": "Editorial insurance illustration",
                    "alt_text": "Expat health insurance illustration",
                    "materialization_status": "materialized",
                    "asset_ref": "media_1",
                }]
            },
            "linking": {
                "internal": [{
                    "link_id": "link_internal_1",
                    "section_index": 0,
                    "target_url": "https://insurancereviewlab.com/insurance/",
                    "anchor_text": "insurance coverage",
                    "placement": "body",
                }],
                "external": [],
            },
            "taxonomy": {"categories": ["Expat Insurance"], "tags": ["health insurance"]},
            "production_intent": {
                "target": "wordpress",
                "mode": "wordpress_draft",
                "publish": False,
                "human_approval_required": True,
            },
        },
        "audit": {"method": "production_assembly", "version": "v1", "validation_status": "validated"},
    }


def _errors(value: dict) -> list:
    validator = Draft202012Validator(_schema(), format_checker=FormatChecker())
    return sorted(validator.iter_errors(value), key=lambda error: list(error.path))


def test_production_assembly_ready_is_valid():
    assert _errors(_assembly()) == []


def test_pending_assembly_stage_is_valid_without_validated_audit():
    assembly = _assembly(stage="assembly_started")
    assembly["audit"]["validation_status"] = "pending"
    assert _errors(assembly) == []


def test_failed_stage_requires_failed_audit():
    assembly = _assembly(stage="failed")
    assembly["audit"]["validation_status"] = "pending"
    assert _errors(assembly)


def test_missing_required_artifact_is_rejected():
    assembly = _assembly()
    del assembly["artifacts"]["taxonomy"]
    assert _errors(assembly)


def test_unsafe_production_intent_is_rejected():
    assembly = _assembly()
    assembly["artifacts"]["production_intent"]["publish"] = True
    assert _errors(assembly)


def test_unmaterialized_media_is_rejected_at_ready_stage():
    assembly = _assembly()
    assembly["artifacts"]["media"]["images"][0]["materialization_status"] = "specified"
    assembly["artifacts"]["media"]["images"][0].pop("asset_ref")
    assert _errors(assembly)


def test_materialized_media_requires_asset_ref():
    assembly = _assembly()
    assembly["artifacts"]["media"]["images"][0].pop("asset_ref")
    assert _errors(assembly)


def test_taxonomy_requires_category():
    assembly = _assembly()
    assembly["artifacts"]["taxonomy"]["categories"] = []
    assert _errors(assembly)


def test_lineage_required_fields_are_enforced():
    assembly = _assembly()
    del assembly["lineage"]["draft_id"]
    assert _errors(assembly)


def test_schema_rejects_unknown_top_level_fields():
    assembly = _assembly()
    assembly["unexpected"] = True
    assert _errors(assembly)


def test_schema_validation_does_not_mutate_fixture():
    assembly = _assembly()
    original = copy.deepcopy(assembly)
    _errors(assembly)
    assert assembly == original
