from agents.research.analyzers.serp_intent import analyze_serp_intent


def test_serp_intent_analysis():
    serp_data = {
        "keyword": "best expat health insurance",
        "language": "en",
        "country": "US",
        "results": [
            {
                "position": 1,
                "title": "Best Expat Health Insurance Plans",
                "url": "https://example.com/best-expat-health-insurance",
                "domain": "example.com",
                "snippet": "Compare the best plans and providers.",
            },
            {
                "position": 2,
                "title": "Expat Health Insurance Guide",
                "url": "https://example.org/guide",
                "domain": "example.org",
                "snippet": "Learn how expat health insurance works.",
            },
        ],
    }

    result = analyze_serp_intent(serp_data)

    assert result["keyword"] == "best expat health insurance"
    assert result["dominant_intent"] in {
        "Informational",
        "Commercial",
        "Transactional",
        "Navigational",
    }
    assert 0 <= result["dominant_confidence"] <= 1
    assert len(result["results"]) == 2
    assert all("intent" in item for item in result["results"])
    assert all(0 <= item["confidence"] <= 1 for item in result["results"])


def test_empty_serp_intent_analysis():
    result = analyze_serp_intent(
        {
            "keyword": "example",
            "language": "en",
            "country": "US",
            "results": [],
        }
    )

    assert result["dominant_intent"] is None
    assert result["dominant_confidence"] == 0.0
    assert result["mixed_intent"] is False
    assert result["results"] == []


def test_generic_domain_token_is_not_navigational():
    result = analyze_serp_intent(
        {
            "keyword": "expat health insurance",
            "language": "en",
            "country": "US",
            "results": [
                {
                    "position": 1,
                    "title": "International Health Insurance Coverage for Living Abroad",
                    "url": "https://www.internationalinsurance.com/health/",
                    "domain": "www.internationalinsurance.com",
                    "snippet": "International medical insurance coverage and pricing.",
                }
            ],
        }
    )

    assert result["results"][0]["intent"] != "Navigational"
