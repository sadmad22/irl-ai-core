from __future__ import annotations

import copy

import pytest

from agents.research.ai_images import build_ai_image_spec


LINEAGE = {
    "brief_id": "brief_1",
    "report_id": "report_1",
    "decision_id": "decision_1",
    "strategy_id": "strategy_1",
}


def _strategy() -> dict:
    return {
        **LINEAGE,
        "strategy_id": "strategy_1",
        "lifecycle_stage": "content_strategy_ready",
        "primary_keyword": "expat health insurance",
        "sections": ["Introduction", "Coverage and Key Factors"],
    }


def _config() -> dict:
    return {
        **LINEAGE,
        "config_id": "config_1",
        "lifecycle_stage": "article_config_ready",
        "article_type": "guide",
        "article_size": "standard",
        "target_country": "US",
    }


def _draft() -> dict:
    return {
        **LINEAGE,
        "draft_id": "draft_1",
        "lifecycle_stage": "draft_ready",
        "title": "Expat Health Insurance Guide",
        "primary_keyword": "expat health insurance",
        "sections": [
            {"heading": "Introduction", "purpose": "Introduce the topic."},
            {"heading": "Coverage and Key Factors", "purpose": "Explain key factors."},
        ],
    }


def _build() -> dict:
    return build_ai_image_spec(
        content_strategy=_strategy(),
        article_config=_config(),
        article_draft=_draft(),
    )


def test_engine_output_has_expected_contract_shape():
    result = _build()
    assert result["lifecycle_stage"] == "ai_image_spec_ready"
    assert result["brief_id"] == "brief_1"
    assert result["config_id"] == "config_1"
    assert result["draft_id"] == "draft_1"
    assert len(result["images"]) == 2


def test_engine_maps_first_section_to_hero():
    image = _build()["images"][0]
    assert image["image_type"] == "hero"
    assert image["placement"] == "hero"
    assert image["aspect_ratio"] == "16:9"
    assert image["width"] == 1600
    assert image["height"] == 900


def test_engine_maps_later_sections_to_section_images():
    image = _build()["images"][1]
    assert image["image_type"] == "section"
    assert image["placement"] == "section"
    assert image["section_heading"] == "Coverage and Key Factors"


def test_engine_generates_contextual_prompts():
    result = _build()
    prompt = result["images"][0]["prompt"]
    assert "expat health insurance" in prompt
    assert "Expat Health Insurance Guide" in prompt
    assert "Introduction" in prompt


def test_engine_is_deterministic():
    assert _build() == _build()


def test_engine_does_not_mutate_sources():
    sources = {"strategy": _strategy(), "config": _config(), "draft": _draft()}
    before = copy.deepcopy(sources)
    build_ai_image_spec(
        content_strategy=sources["strategy"],
        article_config=sources["config"],
        article_draft=sources["draft"],
    )
    assert sources == before


@pytest.mark.parametrize(
    "field, expected",
    [
        ("content_strategy", "content_strategy_ready"),
        ("article_config", "article_config_ready"),
        ("article_draft", "draft_ready"),
    ],
)
def test_engine_requires_ready_upstream_lifecycle(field: str, expected: str):
    sources = {
        "content_strategy": _strategy(),
        "article_config": _config(),
        "article_draft": _draft(),
    }
    sources[field]["lifecycle_stage"] = "invalid"
    with pytest.raises(ValueError, match=expected):
        build_ai_image_spec(**sources)


def test_engine_rejects_lineage_mismatch():
    config = _config()
    config["strategy_id"] = "strategy_other"
    with pytest.raises(ValueError, match="lineage mismatch"):
        build_ai_image_spec(
            content_strategy=_strategy(),
            article_config=config,
            article_draft=_draft(),
        )


def test_engine_requires_non_empty_article_sections():
    draft = _draft()
    draft["sections"] = []
    with pytest.raises(ValueError, match="Article Draft.sections"):
        build_ai_image_spec(
            content_strategy=_strategy(),
            article_config=_config(),
            article_draft=draft,
        )


def test_engine_defers_alt_text_and_provider_calls():
    result = _build()
    assert all(image["alt_text_status"] == "pending" for image in result["images"])
    assert result["constraints"]["network_access"] is False
    assert result["constraints"]["provider_call"] is False
