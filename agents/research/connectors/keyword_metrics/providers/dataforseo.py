import requests

API_ENDPOINT = "/v3/keywords_data/google_ads/search_volume/live"

from ..base import KeywordMetricsProvider
from ..config import BASE_URL

class DataForSEOKeywordMetricsProvider(KeywordMetricsProvider):
    """
    Keyword metrics provider using the DataForSEO API.
    """

    def __init__(self):
        self.session = requests.Session()
        self.base_url = BASE_URL

    def get_metrics(
        self,
        keyword: str,
        language: str,
        country: str,
    ) -> dict:

        if self.base_url is None:
            raise RuntimeError("Keyword metrics provider is not configured.")

        return {
            "keyword": keyword,
            "search_volume": 0,
            "difficulty": 0,
            "cpc": 0.0,
            "trend": [],
            "language": language,
            "country": country,
}