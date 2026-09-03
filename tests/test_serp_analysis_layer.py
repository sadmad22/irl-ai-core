import pytest

from agents.research.connectors.serp.base import SERPProvider
from agents.research.serp_analysis_layer import build_serp_analysis


class MockSERPProvider(SERPProvider):
    def __init__(self, payload=None):
        self.payload = payload
        self.calls = []

    def get_results(self, keyword: str, language: str, country: str) -> dict:
        self.calls.append((keyword, language, country))
        return self.payload or {
            "keyword": keyword,
            "language": language,
            "country": country,
            "results": [
                {
                    "position": 1,
                    "title": "Top result",
                    "url": "https://example.com/guide",
                    "domain": "example.com",
                    "snippet": "A useful guide.",
                },
                {
                    "position": 2,
                    "title": "Second result",
                    "url": "https://competitor.com/page",
                    "domain": "competitor.com",
                    "snippet": "Another result.",
                },
            ],
        }


def strategy(**overrides):
    value = {
        "strategy_id": "strategy-1",
        "report_id": "report-1",
        "decision_id": "decision-1",
        "brief_id": "brief-1",
        "schema_version": "1.0",
        "lifecycle_stage": "content_strategy_ready",
        "content_type": "guide",
        "primary_keyword": "expat health insurance",
        "audience": "Expats comparing international health insurance",
        "angle": "Evidence-led comparison",
        "format": "structured guide",
        "sections": ["Coverage", "Costs", "Providers"],
        "entities": ["Cigna Global", "Allianz Care"],
        "questions": ["How much does expat health insurance cost?"],
        "business_goal": "Build qualified organic traffic.",
        "evidence_refs": ["evidence-1"],
    }
    value.update(overrides)
    return value


def config(**overrides):
    value = {
        "config_id": "config-1",
        "brief_id": "brief-1",
        "report_id": "report-1",
        "decision_id": "decision-1",
        "strategy_id": "strategy-1",
        "schema_version": "1.0",
        "lifecycle_stage": "article_config_ready",
        "article_type": "guide",
        "article_size": "standard",
        "target_country": "US",
        "word_target": {"min": 1400, "target": 2000, "max": 2600},
        "heading_target": {"min": 6, "target": 8, "max": 10},
        "h3_target": {"min": 4, "target": 7, "max": 10},
    }
    value.update(overrides)
    return value


def test_builds_serp_and_competitor_contract():
    provider = MockSERPProvider()
    result = build_serp_analysis(
        content_strategy=strategy(),
        article_config=config(),
        provider=provider,
    )

    assert result["lifecycle_stage"] == "serp_analysis_ready"
    assert result["keyword"] == "expat health insurance"
    assert result["country"] == "US"
    assert result["serp"]["results"][0]["position"] == 1
    assert result["competitor_analysis"]["top_competitors"][0]["domain"] == "example.com"
    assert result["audit"]["provider"] == "MockSERPProvider"
    assert provider.calls == [("expat health insurance", "en", "US")]


def test_analysis_id_is_deterministic_for_same_provider_response():
    first = build_serp_analysis(content_strategy=strategy(), article_config=config(), provider=MockSERPProvider())
    second = build_serp_analysis(content_strategy=strategy(), article_config=config(), provider=MockSERPProvider())
    assert first["analysis_id"] == second["analysis_id"]


def test_lineage_must_match():
    with pytest.raises(ValueError, match="lineage"):
        build_serp_analysis(
            content_strategy=strategy(),
            article_config=config(strategy_id="different"),
            provider=MockSERPProvider(),
        )


def test_requires_ready_content_strategy():
    with pytest.raises(ValueError, match="content_strategy_ready"):
        build_serp_analysis(
            content_strategy=strategy(lifecycle_stage="draft"),
            article_config=config(),
            provider=MockSERPProvider(),
        )


def test_requires_ready_article_config():
    with pytest.raises(ValueError, match="article_config_ready"):
        build_serp_analysis(
            content_strategy=strategy(),
            article_config=config(lifecycle_stage="draft"),
            provider=MockSERPProvider(),
        )


def test_provider_metadata_must_match_request():
    provider = MockSERPProvider(
        {
            "keyword": "wrong keyword",
            "language": "en",
            "country": "US",
            "results": [],
        }
    )
    with pytest.raises(ValueError, match="metadata"):
        build_serp_analysis(
            content_strategy=strategy(),
            article_config=config(),
            provider=provider,
        )


def test_empty_results_are_valid():
    provider = MockSERPProvider(
        {"keyword": "expat health insurance", "language": "en", "country": "US", "results": []}
    )
    result = build_serp_analysis(content_strategy=strategy(), article_config=config(), provider=provider)
    assert result["serp"]["results"] == []
    assert result["competitor_analysis"]["competitors"] == []
    assert result["competitor_analysis"]["average_position"] is None
