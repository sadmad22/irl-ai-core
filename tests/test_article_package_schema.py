import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "shared" / "schemas" / "article-package.schema.json"


def _schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _package(content_type="guide", lifecycle_stage="delivery_ready"):
    return {
        "identity": {
            "package_id": "package_0123456789abcdef",
            "project_name": "example-insurance",
            "schema_version": "1.0",
            "lifecycle_stage": lifecycle_stage,
            "content_type": content_type,
            "primary_keyword": "example insurance",
        },
        "lineage": {
            "report_id": "report_123",
            "decision_id": "decision_123",
            "strategy_id": "strategy_123",
            "brief_id": "brief_123",
            "draft_id": "draft_123",
            "quality_id": "quality_123",
        },
        "content": {
            "article": {
                "title": "Example Insurance Guide",
                "slug": "example-insurance-guide",
                "excerpt": "A concise insurance guide.",
            },
            "sections": [
                {
                    "section_id": "section_0",
                    "order": 0,
                    "heading": "Overview",
                    "body": "Evidence-backed article text.",
                    "purpose": "Explain the topic.",
                    "claim_ids": ["claim_0"],
                    "evidence_refs": ["evidence_0"],
                }
            ],
            "claims": [
                {
                    "claim_id": "claim_0",
                    "section_id": "section_0",
                    "text": "Supported claim.",
                    "evidence_refs": ["evidence_0"],
                    "grounding_status": "grounded",
                }
            ],
            "tables": [],
        },
        "media": {
            "images": [
                {
                    "image_id": "image_0",
                    "section_id": "section_0",
                    "placement": "After overview",
                    "prompt": "Editorial insurance illustration.",
                    "alt_text": "Insurance coverage illustration",
                    "materialization_status": "materialized",
                    "asset_ref": "media_artifact_0",
                }
            ],
            "featured_image": {"image_id": "image_0"},
        },
        "linking": {"internal": [], "external": []},
        "optimization": {
            "seo_title": "Example Insurance Guide",
            "meta_description": "Learn the essentials of example insurance.",
            "canonical_url": "https://insurancereviewlab.com/example-insurance-guide/",
        },
        "taxonomy": {"categories": ["Insurance"], "tags": ["Example"]},
        "delivery": {
            "target": "wordpress",
            "mode": "wordpress_draft",
            "publish": False,
            "human_approval_required": True,
        },
        "audit": {
            "method": "article_package_contract",
            "version": "v1",
            "validation_status": "validated",
        },
    }


def _validate(package):
    validator = Draft202012Validator(_schema(), format_checker=FormatChecker())
    return sorted(validator.iter_errors(package), key=lambda error: list(error.path))


def test_valid_delivery_ready_package_passes_schema():
    assert _validate(_package()) == []


def test_comparison_requires_at_least_one_table():
    package = _package(content_type="comparison")
    errors = _validate(package)
    assert any("tables" in error.message or "less than the minimum" in error.message for error in errors)


def test_comparison_with_valid_table_passes():
    package = _package(content_type="comparison")
    package["content"]["tables"] = [
        {
            "table_id": "table_0",
            "title": "Provider comparison",
            "section_id": "section_0",
            "columns": ["Provider", "Coverage"],
            "rows": [["Provider A", "Professional liability"]],
            "evidence_refs": ["evidence_0"],
        }
    ]
    assert _validate(package) == []


def test_delivery_ready_rejects_unmaterialized_image():
    package = _package()
    package["media"]["images"][0]["materialization_status"] = "specified"
    package["media"]["images"][0].pop("asset_ref")
    errors = _validate(package)
    assert any("materialized" in error.message for error in errors)


def test_materialized_image_requires_asset_ref():
    package = _package(lifecycle_stage="package_assembled")
    package["media"]["images"][0].pop("asset_ref")
    errors = _validate(package)
    assert errors
    assert any("asset_ref" in error.message for error in errors)


def test_delivery_ready_requires_grounded_claims():
    package = _package()
    package["content"]["claims"][0]["grounding_status"] = "provisional"
    errors = _validate(package)
    assert any("grounded" in error.message for error in errors)


def test_package_rejects_unsafe_publication_intent():
    package = _package()
    package["delivery"]["publish"] = True
    errors = _validate(package)
    assert errors
    assert any("False" in error.message or "false" in error.message for error in errors)


def test_package_rejects_unknown_root_fields():
    package = _package()
    package["unexpected"] = "must fail closed"
    errors = _validate(package)
    assert errors
    assert any("additional properties" in error.message for error in errors)


def test_package_rejects_invalid_uri():
    package = _package()
    package["optimization"]["canonical_url"] = "not-a-uri"
    errors = _validate(package)
    assert errors


def test_package_fixture_is_not_mutated_by_validation():
    package = _package()
    before = copy.deepcopy(package)
    _validate(package)
    assert package == before
