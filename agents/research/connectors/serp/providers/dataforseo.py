import requests

API_ENDPOINT = "/v3/serp/google/organic/live/advanced"

from ..base import SERPProvider
from ..config import BASE_URL, LOGIN, PASSWORD


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
            "url": item["url"],
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