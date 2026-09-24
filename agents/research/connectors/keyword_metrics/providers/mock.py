from ..base import KeywordMetricsProvider, validate_keyword_metrics_response


class MockKeywordMetricsProvider(KeywordMetricsProvider):
    """Explicit mock provider for contract and unit tests."""

    provider_name = "mock"

    def get_metrics(self, keyword: str, language: str, country: str) -> dict:
        payload = {
            "provider": self.provider_name,
            "keyword": keyword,
            "search_volume": 1000,
            "competition": 35,
            "cpc": 1.25,
            "trend": [],
            "language": language,
            "country": country,
        }
        return validate_keyword_metrics_response(
            payload,
            expected_provider=self.provider_name,
        )
