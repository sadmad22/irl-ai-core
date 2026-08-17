from agents.research.analyzers.entity import analyze_entities
from agents.research.analyzers.question import analyze_questions
from agents.research.analyzers.business import analyze_business
from agents.research.analyzers.authority import analyze_authority


def _serp():
    return {
        "results": [
            {"position": 1, "domain": "example.com", "title": "What is expat health insurance?", "snippet": "How does coverage work?"},
            {"position": 2, "domain": "example.org", "title": "Best expat health insurance", "snippet": "Compare plans and costs."},
            {"position": 3, "domain": "example.com", "title": "Expat medical insurance", "snippet": "Coverage guide."},
        ]
    }


def test_entity_analyzer_returns_ranked_organization_entities():
    result = analyze_entities(_serp())
    assert result["entity_count"] == 2
    assert result["entities"][0]["entity_type"] == "organization"
    assert result["entities"][0]["mentioned"] is True
    assert 0 <= result["entities"][0]["relevance"] <= 1


def test_entity_analyzer_is_deterministic():
    assert analyze_entities(_serp()) == analyze_entities(_serp())


def test_question_analyzer_counts_question_shaped_results():
    result = analyze_questions(_serp())
    assert result["question_count"] >= 2
    assert result["result_question_count"] >= 1


def test_question_analyzer_is_deterministic():
    assert analyze_questions(_serp()) == analyze_questions(_serp())


def test_business_analyzer_produces_minimum_business_signals():
    result = analyze_business(
        {"keyword": "best expat health insurance"},
        {"primary_intent": "Commercial", "confidence": 0.9},
        {"search_volume": 1000, "cpc": 2.5, "competition": 0.2},
    )
    assert result["commercial_value"] in {"low", "medium", "high"}
    assert 0 <= result["commercial_value_score"] <= 1
    assert 0 <= result["competition_signal"] <= 1


def test_authority_analyzer_produces_normalized_scores():
    result = analyze_authority(
        {"keyword": "expat health insurance"},
        _serp(),
        {"domain_counts": {"example.com": 2, "example.org": 1}},
        {"primary_intent": "Commercial", "confidence": 0.9},
    )
    assert 0 <= result["authority_score"] <= 1
    assert 0 <= result["topic_fit"] <= 1
    assert result["serp_domain_count"] == 2


def test_authority_analyzer_is_deterministic():
    args = (
        {"keyword": "expat health insurance"},
        _serp(),
        {"domain_counts": {"example.com": 2, "example.org": 1}},
        {"primary_intent": "Commercial", "confidence": 0.9},
    )
    assert analyze_authority(*args) == analyze_authority(*args)
