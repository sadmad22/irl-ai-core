from __future__ import annotations

import copy

import pytest

from agents.research.alt_text import build_alt_text_contract


def _upstream() -> tuple[dict, dict]:
    image_spec = {
        "image_spec_id": "imgspec_1", "brief_id": "brief_1", "report_id": "report_1",
        "decision_id": "decision_1", "strategy_id": "strategy_1", "config_id": "config_1",
        "draft_id": "draft_1", "schema_version": "1.0", "lifecycle_stage": "ai_image_spec_ready",
        "images": [
            {"image_id": "image_1", "image_type": "hero", "section_index": 0,
             "section_heading": "Introduction", "purpose": "Establish the consultant insurance topic visually.",
             "prompt": "prompt", "aspect_ratio": "16:9", "width": 1600, "height": 900,
             "placement": "hero", "alt_text_status": "pending"},
            {"image_id": "image_2", "image_type": "section", "section_index": 1,
             "section_heading": "Professional Liability Coverage", "purpose": "Explain professional liability coverage for consultants.",
             "prompt": "prompt", "aspect_ratio": "16:9", "width": 1600, "height": 900,
             "placement": "section", "alt_text_status": "pending"},
        ],
        "constraints": {"network_access": False, "provider_call": False,
                         "brand_style_included": False, "media_strategy_included": False},
        "audit": {"method": "test", "version": "v1", "validation_status": "validated"},
    }
    draft = {
        "draft_id": "draft_1", "brief_id": "brief_1", "report_id": "report_1",
        "decision_id": "decision_1", "strategy_id": "strategy_1", "schema_version": "1.0",
        "lifecycle_stage": "draft_ready", "title": "Consultant Insurance Guide",
        "content_type": "guide", "primary_keyword": "consultant insurance", "sections": [],
    }
    return image_spec, draft


def test_engine_builds_one_alt_text_per_image():
    image_spec, draft = _upstream()
    result = build_alt_text_contract(image_spec=image_spec, article_draft=draft)
    assert result["lifecycle_stage"] == "alt_text_ready"
    assert len(result["alt_texts"]) == len(image_spec["images"])
    assert [item["image_id"] for item in result["alt_texts"]] == ["image_1", "image_2"]


def test_engine_preserves_lineage_and_identity():
    image_spec, draft = _upstream()
    result = build_alt_text_contract(image_spec=image_spec, article_draft=draft)
    for field in ("brief_id", "report_id", "decision_id", "strategy_id"):
        assert result[field] == image_spec[field] == draft[field]
    assert result["config_id"] == image_spec["config_id"]
    assert result["draft_id"] == draft["draft_id"]
    assert result["image_spec_id"] == image_spec["image_spec_id"]


@pytest.mark.parametrize("artifact, lifecycle", [("image_spec", "wrong"), ("draft", "wrong")])
def test_engine_requires_ready_lifecycles(artifact, lifecycle):
    image_spec, draft = _upstream()
    {"image_spec": image_spec, "draft": draft}[artifact]["lifecycle_stage"] = lifecycle
    with pytest.raises(ValueError):
        build_alt_text_contract(image_spec=image_spec, article_draft=draft)


def test_engine_rejects_lineage_mismatch():
    image_spec, draft = _upstream()
    draft["strategy_id"] = "strategy_other"
    with pytest.raises(ValueError, match="lineage mismatch"):
        build_alt_text_contract(image_spec=image_spec, article_draft=draft)


def test_engine_is_deterministic():
    image_spec, draft = _upstream()
    first = build_alt_text_contract(image_spec=image_spec, article_draft=draft)
    second = build_alt_text_contract(image_spec=image_spec, article_draft=draft)
    assert first == second


def test_engine_does_not_mutate_inputs():
    image_spec, draft = _upstream()
    before = (copy.deepcopy(image_spec), copy.deepcopy(draft))
    build_alt_text_contract(image_spec=image_spec, article_draft=draft)
    assert (image_spec, draft) == before


def test_engine_outputs_ready_status_and_accessibility_constraints():
    image_spec, draft = _upstream()
    result = build_alt_text_contract(image_spec=image_spec, article_draft=draft)
    assert all(item["status"] == "ready" and item["alt_text"].strip() for item in result["alt_texts"])
    assert all(len(item["alt_text"]) <= 250 for item in result["alt_texts"])
    assert result["constraints"] == {
        "network_access": False, "provider_call": False, "image_analysis_call": False,
        "keyword_stuffing": False, "image_spec_mutation": False,
    }


def test_engine_uses_image_context_without_keyword_stuffing():
    image_spec, draft = _upstream()
    result = build_alt_text_contract(image_spec=image_spec, article_draft=draft)
    for item in result["alt_texts"]:
        assert item["alt_text"].lower().count("consultant insurance") <= 1


def test_engine_falls_back_when_purpose_is_missing():
    image_spec, draft = _upstream()
    image_spec["images"][1]["purpose"] = ""
    result = build_alt_text_contract(image_spec=image_spec, article_draft=draft)
    assert result["alt_texts"][1]["alt_text"] == "Illustration for Professional Liability Coverage"


def test_engine_rejects_missing_primary_keyword():
    image_spec, draft = _upstream()
    draft["primary_keyword"] = ""
    with pytest.raises(ValueError, match="primary keyword"):
        build_alt_text_contract(image_spec=image_spec, article_draft=draft)


def test_engine_rejects_invalid_image_entries():
    image_spec, draft = _upstream()
    image_spec["images"] = [{"image_id": "image_1", "section_heading": "Introduction", "section_index": True}]
    with pytest.raises(ValueError):
        build_alt_text_contract(image_spec=image_spec, article_draft=draft)
