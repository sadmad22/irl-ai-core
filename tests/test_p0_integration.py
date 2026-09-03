from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.p0_integration import build_p0_integration


SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "shared"
    / "schemas"
    / "p0-integration.schema.json"
)


LINEAGE = {
    "brief_id": "brief_001",
    "report_id": "report_001",
    "decision_id": "decision_001",
    "strategy_id": "strategy_001",
}


def _quality():
    return {
        **LINEAGE,
        "quality_id": "quality_001",
        "lifecycle_stage": "article_draft_quality_ready",
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
    }


def _seo():
    return {
        **LINEAGE,
        "seo_strategy_id": "seo_001",
        "seo_validation_id": "seo_validation_001",
        "lifecycle_stage": "seo_validation_ready",
        "outcome": "passed",
        "checks": {
            "primary_keyword": True,
            "title": True,
            "headings": True,
            "evidence_lineage": True,
            "structure": True,
        },
    }


def _semantic():
    return {
        **LINEAGE,
        "semantic_id": "semantic_001",
        "lifecycle_stage": "semantic_seo_ready",
        "primary_keyword": "expat health insurance",
        "secondary_keywords": ["international health insurance"],
        "semantic_keywords": [
            "international health coverage",
            "expat medical coverage",
        ],
        "entities": ["Cigna Global", "Allianz Care"],
        "questions": [
            "What is expat health insurance?"
        ],
        "section_keyword_map": [
            {
                "section": "Cost",
                "keywords": ["expat health insurance"],
            }
        ],
    }


def _serp():
    return {
        **LINEAGE,
        "analysis_id": "serp_001",
        "lifecycle_stage": "serp_analysis_ready",
        "keyword": "expat health insurance",
        "language": "en",
        "country": "US",
        "serp": {
            "keyword": "expat health insurance",
            "language": "en",
            "country": "US",
            "results": [
                {
                    "position": 1,
                    "title": "Example",
                }
            ],
        },
        "competitor_analysis": {
            "competitors": []
        },
    }


def _config():
    return {
        **LINEAGE,
        "config_id": "config_001",
        "lifecycle_stage": "article_config_ready",
        "article_type": "guide",
        "article_size": "standard",
        "target_country": "US",
        "word_target": {
            "min": 1400,
            "target": 2000,
            "max": 2600,
        },
        "heading_target": {
            "min": 6,
            "target": 8,
            "max": 10,
        },
        "h3_target": {
            "min": 4,
            "target": 7,
            "max": 10,
        },
    }


def _build():
    return build_p0_integration(
        article_draft_quality=_quality(),
        seo_validation=_seo(),
        semantic_seo=_semantic(),
        serp_analysis=_serp(),
        article_config=_config(),
    )


def test_p0_integration_matches_schema():
    schema = json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )

    result = _build()

    Draft202012Validator(schema).validate(result)


def test_builds_p0_integration_from_existing_contracts():
    result = _build()

    assert result["lifecycle_stage"] == "p0_integration_ready"
    assert result["brief_id"] == "brief_001"

    assert result["signals"]["quality"]["available"] is True
    assert result["signals"]["quality"]["passed_checks"] == 8

    assert result["signals"]["seo"]["available"] is True
    assert result["signals"]["seo"]["passed_checks"] == 5

    assert result["signals"]["semantic"]["semantic_keyword_count"] == 2
    assert result["signals"]["semantic"]["entity_count"] == 2

    assert result["signals"]["competitive"]["result_count"] == 1

    assert (
        result["signals"]["configuration"]["target_country"]
        == "US"
    )


def test_content_score_is_not_calculated_yet():
    result = _build()

    assert result["content_score"] is None
    assert (
        result["audit"]["content_score_status"]
        == "not_calculated"
    )


def test_integration_id_is_deterministic():
    assert _build()["integration_id"] == _build()["integration_id"]


@pytest.mark.parametrize(
    "field",
    [
        "article_draft_quality",
        "seo_validation",
        "semantic_seo",
        "serp_analysis",
        "article_config",
    ],
)
def test_requires_expected_lifecycle(field):
    inputs = {
        "article_draft_quality": _quality(),
        "seo_validation": _seo(),
        "semantic_seo": _semantic(),
        "serp_analysis": _serp(),
        "article_config": _config(),
    }

    inputs[field] = copy.deepcopy(inputs[field])
    inputs[field]["lifecycle_stage"] = "invalid"

    with pytest.raises(ValueError):
        build_p0_integration(**inputs)


def test_rejects_lineage_mismatch():
    semantic = _semantic()
    semantic["strategy_id"] = "strategy_other"

    with pytest.raises(ValueError, match="lineage mismatch"):
        build_p0_integration(
            article_draft_quality=_quality(),
            seo_validation=_seo(),
            semantic_seo=semantic,
            serp_analysis=_serp(),
            article_config=_config(),
        )


def test_does_not_mutate_source_contracts():
    sources = {
        "quality": _quality(),
        "seo": _seo(),
        "semantic": _semantic(),
        "serp": _serp(),
        "config": _config(),
    }

    before = copy.deepcopy(sources)

    build_p0_integration(
        article_draft_quality=sources["quality"],
        seo_validation=sources["seo"],
        semantic_seo=sources["semantic"],
        serp_analysis=sources["serp"],
        article_config=sources["config"],
    )

    assert sources == before