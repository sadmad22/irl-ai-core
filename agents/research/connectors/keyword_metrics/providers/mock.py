from ..base import KeywordMetricsProvider


class MockKeywordMetricsProvider(KeywordMetricsProvider):
    """
    Temporary provider used to test the connector architecture.
    """

    def get_metrics(
        self,
        keyword: str,
        language: str,
        country: str,
    ) -> dict:

        return {
            "keyword": keyword,
            "search_volume": 1000,
            "difficulty": 35,
            "cpc": 1.25,
            "trend": [],
            "language": language,
            "country": country,
        }