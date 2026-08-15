from agents.research.analyzers.competitor import analyze_competitors


def test_competitor_analysis():
    serp_data = {
        "keyword": "expat health insurance",
        "language": "en",
        "country": "US",
        "results": [
            {
                "position": 2,
                "title": "Example Result",
                "url": "https://example.com/page",
                "domain": "example.com",
                "snippet": "Example snippet",
            },
            {
                "position": 5,
                "title": "Another Result",
                "url": "https://example.org/page",
                "domain": "example.org",
                "snippet": "Another snippet",
            },
        ],
    }

    result = analyze_competitors(serp_data)

    assert result["keyword"] == "expat health insurance"
    assert result["country"] == "US"
    assert result["language"] == "en"
    assert len(result["competitors"]) == 2
    assert result["top_competitors"][0]["domain"] == "example.com"
    assert result["domain_counts"]["example.com"] == 1