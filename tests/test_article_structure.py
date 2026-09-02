import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.article_structure import build_article_structure_contract


def _brief():
    return {
        "brief_id": "brief_001",
        "report_id": "rr_001",
        "decision_id": "dec_001",
        "strategy_id": "strat_001",
        "schema_version": "1.0",
        "lifecycle_stage": "content_brief_ready",
    }


def _structure():
    return {
        "hook": {"required": True, "hook_type": "question"},
        "conclusion": {"required": True},
        "h3": {"min": 4, "max": 8},
        "tables": {"enabled": True, "required": True, "count": {"min": 1, "max": 3}},
        "lists": {"enabled": True, "required": False, "count": {"min": 2, "max": 6}},
        "faq": {"enabled": True, "required": True, "answer_required": True, "count": {"min": 5, "max": 8}},
    }


def test_article_structure_contract_shape():
    result = build_article_structure_contract(content_brief=_brief(), structure=_structure())
    assert result["lifecycle_stage"] == "article_structure_ready"
    assert result["brief_id"] == "brief_001"
    assert result["hook"]["hook_type"] == "question"
    assert result["conclusion"] == {"required": True}
    assert result["h3"] == {"min": 4, "max": 8}
    assert result["tables"]["count"] == {"min": 1, "max": 3}
    assert result["lists"]["count"] == {"min": 2, "max": 6}
    assert result["faq"]["count"] == {"min": 5, "max": 8}


def test_article_structure_contract_is_deterministic():
    first = build_article_structure_contract(content_brief=_brief(), structure=_structure())
    second = build_article_structure_contract(content_brief=_brief(), structure=_structure())
    assert first == second
    assert first["structure_id"] == second["structure_id"]


def test_article_structure_does_not_mutate_inputs():
    brief = _brief()
    structure = _structure()
    brief_snapshot = copy.deepcopy(brief)
    structure_snapshot = copy.deepcopy(structure)
    build_article_structure_contract(content_brief=brief, structure=structure)
    assert brief == brief_snapshot
    assert structure == structure_snapshot


def test_article_structure_requires_ready_content_brief():
    brief = _brief()
    brief["lifecycle_stage"] = "draft_ready"
    with pytest.raises(ValueError, match="content_brief_ready"):
        build_article_structure_contract(content_brief=brief, structure=_structure())


def test_hook_type_is_constrained():
    structure = _structure()
    structure["hook"]["hook_type"] = "made_up"
    with pytest.raises(ValueError, match="supported hook types"):
        build_article_structure_contract(content_brief=_brief(), structure=structure)


def test_required_feature_cannot_be_disabled():
    structure = _structure()
    structure["tables"] = {"enabled": False, "required": True, "count": {"min": 0, "max": 0}}
    with pytest.raises(ValueError, match="required cannot be true"):
        build_article_structure_contract(content_brief=_brief(), structure=structure)


def test_disabled_feature_has_zero_count():
    structure = _structure()
    structure["lists"] = {"enabled": False, "required": False, "count": {"min": 1, "max": 2}}
    with pytest.raises(ValueError, match="count must be zero"):
        build_article_structure_contract(content_brief=_brief(), structure=structure)


def test_ranges_cannot_be_inverted():
    structure = _structure()
    structure["h3"] = {"min": 8, "max": 4}
    with pytest.raises(ValueError, match="min cannot exceed"):
        build_article_structure_contract(content_brief=_brief(), structure=structure)


def test_faq_requires_answers_by_default():
    result = build_article_structure_contract(
        content_brief=_brief(),
        structure={
            **_structure(),
            "faq": {"enabled": True, "required": True, "count": {"min": 1, "max": 2}},
        },
    )
    assert result["faq"]["answer_required"] is True


def test_schema_validates_generated_contract():
    result = build_article_structure_contract(content_brief=_brief(), structure=_structure())
    schema = json.loads((Path(__file__).resolve().parents[1] / "shared" / "schemas" / "article-structure.schema.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(result))
    assert errors == []


def test_contract_has_no_article_prose_or_decision_fields():
    result = build_article_structure_contract(content_brief=_brief(), structure=_structure())
    assert "body" not in result
    assert "decision" not in result
    assert "recommendation" not in result
