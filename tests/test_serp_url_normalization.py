from agents.research.connectors.serp.providers.dataforseo import normalize_serp_url


def test_removes_known_tracking_parameters():
    url = "https://example.com/page?utm_source=google&srsltid=abc123&gclid=test"
    assert normalize_serp_url(url) == "https://example.com/page"


def test_removes_utm_parameter_variants():
    url = "https://example.com/page?utm_medium=cpc&utm_campaign=test&fbclid=abc"
    assert normalize_serp_url(url) == "https://example.com/page"


def test_preserves_functional_parameters():
    url = "https://example.com/page?plan=global&region=us&utm_source=google"
    assert normalize_serp_url(url) == "https://example.com/page?plan=global&region=us"
