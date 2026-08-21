from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agents.research.article_draft_quality import validate_article_draft_quality


def draft():
    return {
        "draft_id": "draft_1",
        "brief_id": "brief_1",
        "report_id": "report_1",
        "decision_id": "decision_1",
        "strategy_id": "strategy_1",
        "schema_version": "1.0",
        "lifecycle_stage": "draft_ready",
        "title": "A Practical Guide to Accountant Insurance",
        "content_type": "guide",
        "primary_keyword": "accountant insurance",
        "sections": [
            {
                "heading": "Coverage",
                "purpose": "Explain the core coverage.",
                "body": "Accountants may evaluate professional liability coverage based on their services and risk profile.",
                "evidence_refs": ["e1", "e2"],
            }
        ],
        "evidence_refs": ["e1", "e2"],
        "editorial_constraints": ["verify factual claims"],
        "audit": {"method": "test", "version": "v1", "validation_status": "pending"},
    }


def test_passes_valid_draft():
    result = validate_article_draft_quality(article_draft=draft())
    assert result["outcome"] == "passed"
    assert result["lifecycle_stage"] == "article_draft_quality_ready"
    assert all(result["checks"].values())


def test_preserves_lineage():
    result = validate_article_draft_quality(article_draft=draft())
    assert result["draft_id"] == "draft_1"
    assert result["brief_id"] == "brief_1"
    assert result["report_id"] == "report_1"
    assert result["decision_id"] == "decision_1"
    assert result["strategy_id"] == "strategy_1"


def test_is_deterministic():
    first = validate_article_draft_quality(article_draft=draft())
    second = validate_article_draft_quality(article_draft=draft())
    assert first == second


def test_does_not_mutate_input():
    value = draft()
    snapshot = copy.deepcopy(value)
    validate_article_draft_quality(article_draft=value)
    assert value == snapshot


def test_requires_draft_ready():
    value = draft()
    value["lifecycle_stage"] = "draft_pending"
    try:
        validate_article_draft_quality(article_draft=value)
    except ValueError as exc:
        assert "draft_ready" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_detects_placeholder_body():
    value = draft()
    value["sections"][0]["body"] = "Draft this section to Address the requirement from the approved content strategy."
    result = validate_article_draft_quality(article_draft=value)
    assert result["outcome"] == "needs_revision"
    assert result["checks"]["placeholders"] is False
    assert any(f["category"] == "placeholders" for f in result["findings"])


def test_detects_upstream_evidence_placeholder():
    value = draft()
    value["sections"][0]["body"] = "Use the upstream evidence_refs for factual claims."
    result = validate_article_draft_quality(article_draft=value)
    assert result["checks"]["placeholders"] is False


def test_detects_decision_engine_leakage():
    value = draft()
    value["recommendation"] = {"provider": "Example"}
    result = validate_article_draft_quality(article_draft=value)
    assert result["outcome"] == "needs_revision"
    assert result["checks"]["decision_engine_leakage"] is False


def test_detects_missing_evidence_refs():
    value = draft()
    value["evidence_refs"] = []
    result = validate_article_draft_quality(article_draft=value)
    assert result["outcome"] == "needs_revision"
    assert result["checks"]["evidence_lineage"] is False
    assert result["checks"]["contract"] is False


def test_detects_missing_section_evidence_refs():
    value = draft()
    del value["sections"][0]["evidence_refs"]
    result = validate_article_draft_quality(article_draft=value)
    assert result["outcome"] == "needs_revision"
    assert result["checks"]["section_evidence_grounding"] is False
    assert result["checks"]["contract"] is False


def test_detects_section_ref_outside_top_level_lineage():
    value = draft()
    value["sections"][0]["evidence_refs"] = ["outside"]
    result = validate_article_draft_quality(article_draft=value)
    assert result["outcome"] == "needs_revision"
    assert result["checks"]["section_evidence_grounding"] is False


def test_detects_incomplete_section():
    value = draft()
    value["sections"][0]["body"] = ""
    result = validate_article_draft_quality(article_draft=value)
    assert result["outcome"] == "needs_revision"
    assert result["checks"]["structure"] is False


def test_quality_result_matches_schema():
    schema_path = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "article-draft-quality.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    result = validate_article_draft_quality(article_draft=draft())
    Draft202012Validator(schema).validate(result)
