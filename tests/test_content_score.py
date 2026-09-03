from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.content_score import build_content_score


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "content-score.schema.json"


LINEAGE = {
    "brief_id": "brief_001",
    "report_id": "report_001",
    "decision_id": "decision_001",
    "strategy_id": "strategy_001",
}


def _integration():
    return {
        **LINEAGE,
        "integration_id": "p0_integration_001",
        "schema_version": "1.0",
        "lifecycle_stage": "p0_integration_ready",
        "signals": {
            "quality": {
                "available": True,
                "outcome": "passed",
                "checks": {
                    "contract": True,
                    "lineage": True,
                    "structure": True,
                    "evidence_lineage": True,
                    "section_evidence_grounding": True,
                    "claim_evidence_grounding": True,
                    "placeholders": True,
                    "decision_engine_leakage": True,
                },
                "source": {"contract": "article_draft_quality", "quality_id": "quality_001"},
            },
            "seo": {
                "available": True,
                "outcome": "passed",
                "checks": {
                    "primary_keyword": True,
                    "title": True,
                    "headings": False,
                    "evidence_lineage": True,
                    "structure": True,
                },
                "source": {"contract": "seo_validation", "seo_validation_id": "seo_001"},
            },
            "semantic": {
                "available": True,
                "primary_keyword": "expat health insurance",
                "secondary_keyword_count": 3,
                "semantic_keyword_count": 8,
                "entity_count": 4,
                "question_count": 3,
                "mapped_section_count": 5,
                "source": {"contract": "semantic_seo", "semantic_id": "semantic_001"},
            },
            "competitive": {
                "available": True,
                "keyword": "expat health insurance",
                "language": "en",
                "country": "US",
                "result_count": 10,
                "competitor_analysis": {},
                "source": {"contract": "serp_analysis", "analysis_id": "serp_001"},
            },
            "configuration": {
                "available": True,
                "article_type": "guide",
                "article_size": "standard",
                "target_country": "US",
                "word_target": {"min": 1500, "target": 2000, "max": 2500},
                "heading_target": {"min": 8, "target": 10, "max": 14},
                "h3_target": {"min": 4, "target": 6, "max": 10},
                "source": {"contract": "article_configuration", "config_id": "config_001"},
            },
        },
        "content_score": None,
        "audit": {
            "method": "p0_existing_contract_signal_integration",
            "version": "v1",
            "validation_status": "validated",
            "content_score_status": "not_calculated",
        },
    }


def _build():
    return build_content_score(p0_integration=_integration())


def test_content_score_matches_schema():
    document = _build()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(document))
    assert errors == []


def test_builds_weighted_score_from_non_overlapping_checks():
    document = _build()
    assert document["score"] == 88.33
    assert document["components"]["quality"]["score"] == 100.0
    assert document["components"]["seo"]["score"] == 66.67
    assert document["components"]["quality"]["weight"] == 0.65
    assert document["components"]["seo"]["weight"] == 0.35
    assert document["scoring_policy"]["seo_scored_checks"] == ["primary_keyword", "title", "headings"]


def test_semantic_serp_and_configuration_are_context_not_score_inputs():
    document = _build()
    for name in ("semantic", "competitive", "configuration"):
        assert document["context"][name]["available"] is True
        assert document["context"][name]["scored"] is False


def test_deterministic_id():
    assert _build()["content_score_id"] == _build()["content_score_id"]


def test_preserves_lineage_and_integration_id():
    document = _build()
    assert {key: document[key] for key in LINEAGE} == LINEAGE
    assert document["integration_id"] == "p0_integration_001"


def test_does_not_mutate_source():
    source = _integration()
    before = copy.deepcopy(source)
    build_content_score(p0_integration=source)
    assert source == before


def test_requires_p0_integration_ready():
    source = _integration()
    source["lifecycle_stage"] = "draft_ready"
    with pytest.raises(ValueError, match="p0_integration_ready"):
        build_content_score(p0_integration=source)


def test_requires_boolean_quality_checks():
    source = _integration()
    source["signals"]["quality"]["checks"]["contract"] = 1
    with pytest.raises(ValueError, match="must be boolean"):
        build_content_score(p0_integration=source)


def test_requires_all_scored_seo_checks():
    source = _integration()
    del source["signals"]["seo"]["checks"]["headings"]
    with pytest.raises(ValueError, match="seo.headings"):
        build_content_score(p0_integration=source)


def test_rejects_unavailable_context_signal():
    source = _integration()
    source["signals"]["semantic"]["available"] = False
    with pytest.raises(ValueError, match="semantic must be available"):
        build_content_score(p0_integration=source)
