import requests

API_ENDPOINT = "/v3/keywords_data/google_ads/search_volume/live"

from ..base import KeywordMetricsProvider
from ..config import BASE_URL, LOGIN, PASSWORD, LOCATION_CODES

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

        url = self.base_url + API_ENDPOINT

        if country not in LOCATION_CODES:
             raise ValueError(f"Unsupported country: {country}")

        payload = [
            {
                "keywords": [keyword],
                "language_code": language,
                "location_code": LOCATION_CODES[country],
            }

]

        response = self.session.post(
         url,
         auth=(LOGIN, PASSWORD),
         json=payload,
)

        response.raise_for_status()

        data = response.json()

        task = data["tasks"][0]

        if task["result_count"] == 0:
            return {
                "keyword": keyword,
                "search_volume": 0,
                "difficulty": 0,
                "cpc": 0.0,
                "trend": [],
                "language": language,
                "country": country,
            }

        result = task["result"][0]

        return {
            "keyword": result["keyword"],
            "search_volume": result["search_volume"],
            "difficulty": result["competition_index"],
            "cpc": result["cpc"],
            "trend": result["monthly_searches"],
            "language": result["language_code"],
            "country": country,
        }