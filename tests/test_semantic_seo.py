import pytest

from agents.research.connectors.keyword_metrics.providers.mock import MockKeywordMetricsProvider
from agents.research.semantic_seo import build_semantic_seo


def strategy(**overrides):
    value = {
        "strategy_id": "strategy-1",
        "report_id": "report-1",
        "decision_id": "decision-1",
        "schema_version": "1.0",
        "lifecycle_stage": "content_strategy_ready",
        "content_type": "guide",
        "primary_keyword": "consultant insurance",
        "audience": "Consultants comparing professional insurance options",
        "angle": "Evidence-led guide to consultant insurance coverage and costs",
        "format": "structured long-form guide",
        "sections": [
            "Introduction",
            "Coverage and Key Factors",
            "Costs and Pricing Factors",
            "How to Compare Options",
            "Frequently Asked Questions",
        ],
        "entities": ["Professional Liability Insurance", "Cyber Insurance", "Cigna"],
        "questions": ["What does consultant insurance cover?", "How much does consultant insurance cost?"],
        "business_goal": "Build qualified organic traffic and provide trustworthy insurance guidance.",
        "evidence_refs": ["evidence-1"],
    }
    value.update(overrides)
    return value


def test_builds_semantic_contract_from_content_strategy():
    result = build_semantic_seo(content_strategy=strategy())
    assert result["lifecycle_stage"] == "semantic_seo_ready"
    assert result["strategy_id"] == "strategy-1"
    assert result["primary_keyword"] == "consultant insurance"
    assert result["questions"] == strategy()["questions"]
    assert len(result["section_keyword_map"]) == 5


def test_semantic_id_is_deterministic():
    first = build_semantic_seo(content_strategy=strategy())
    second = build_semantic_seo(content_strategy=strategy())
    assert first["semantic_id"] == second["semantic_id"]


def test_duplicate_terms_are_normalized():
    result = build_semantic_seo(
        content_strategy=strategy(
            entities=["Cigna", "cigna", " Professional Liability Insurance ", "Cigna"]
        )
    )
    assert result["entities"] == ["Cigna", "Professional Liability Insurance"]


def test_primary_keyword_is_not_repeated_as_semantic_keyword():
    result = build_semantic_seo(
        content_strategy=strategy(
            angle="consultant insurance consultant insurance coverage and costs"
        )
    )
    assert all(value.casefold() != "consultant insurance" for value in result["semantic_keywords"])


def test_section_mapping_always_contains_primary_when_no_overlap_exists():
    result = build_semantic_seo(content_strategy=strategy(sections=["Introduction", "Editorial Methodology"]))
    assert all(section["keywords"] for section in result["section_keyword_map"])
    assert result["section_keyword_map"][0]["keywords"] == ["consultant insurance"]


def test_keyword_metrics_are_optional_and_enriched_through_existing_provider():
    result = build_semantic_seo(
        content_strategy=strategy(),
        keyword_metrics_provider=MockKeywordMetricsProvider(),
        language="en",
        country="US",
    )
    assert result["keyword_metrics"]["keyword"] == "consultant insurance"
    assert result["keyword_metrics"]["country"] == "US"
    assert result["audit"]["metrics_enrichment"] is True


def test_metrics_require_country():
    with pytest.raises(ValueError, match="country"):
        build_semantic_seo(
            content_strategy=strategy(),
            keyword_metrics_provider=MockKeywordMetricsProvider(),
            language="en",
        )


def test_requires_ready_content_strategy():
    with pytest.raises(ValueError, match="content_strategy_ready"):
        build_semantic_seo(content_strategy=strategy(lifecycle_stage="draft"))


def test_requires_strategy_id():
    with pytest.raises(ValueError, match="strategy_id"):
        build_semantic_seo(content_strategy=strategy(strategy_id=""))


def test_requires_primary_keyword():
    with pytest.raises(ValueError, match="primary_keyword"):
        build_semantic_seo(content_strategy=strategy(primary_keyword=" "))


def test_requires_sections():
    with pytest.raises(ValueError, match="sections"):
        build_semantic_seo(content_strategy=strategy(sections=[]))
