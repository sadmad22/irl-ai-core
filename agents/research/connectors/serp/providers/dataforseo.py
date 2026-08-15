import requests
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

API_ENDPOINT = "/v3/serp/google/organic/live/advanced"

from ..base import SERPProvider
from ..config import BASE_URL, LOGIN, PASSWORD


TRACKING_QUERY_PARAMS = {
    "gclid",
    "fbclid",
    "dclid",
    "msclkid",
    "srsltid",
    "_gl",
}


def normalize_serp_url(url: str) -> str:
    """Remove known tracking parameters while preserving functional URL parameters."""
    if not url:
        return url

    parts = urlsplit(url)
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_PARAMS and not key.lower().startswith("utm_")
    ]

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(filtered_query),
            parts.fragment,
        )
    )


class DataForSEOSERPProvider(SERPProvider):
    """
    SERP provider using the DataForSEO API.
    """

    def __init__(self):
        self.session = requests.Session()
        self.base_url = BASE_URL

    def get_results(
        self,
        keyword: str,
        language: str,
        country: str,
    ) -> dict:
        
        url = self.base_url + API_ENDPOINT

        response = self.session.post(
        url,
        auth=(LOGIN, PASSWORD),
        json=[
    {
        "keyword": keyword,
        "language_code": language,
        "location_code": 2840,
    }
],
)

        response.raise_for_status()

        data = response.json()

        task = data["tasks"][0]

        if task["result_count"] == 0:
            return {
               "keyword": keyword,
               "language": language,
               "country": country,
               "results": [],
    }

        results = []

        for item in task["result"][0]["items"]:

         if item["type"] != "organic":
          continue
    
         results.append(
        {
            "position": item["rank_absolute"],
            "title": item["title"],
            "url": normalize_serp_url(item["url"]),
            "domain": item["domain"],
            "snippet": item["description"],
        }
    )

        return {
            "keyword": keyword,
            "language": language,
            "country": country,
            "results": results,
}