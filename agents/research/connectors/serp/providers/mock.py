from ..base import SERPProvider


class MockSERPProvider(SERPProvider):
    """
    Temporary provider used to test the SERP architecture.
    """

    def get_results(
        self,
        keyword: str,
        language: str,
        country: str,
    ) -> dict:

        return {
            "keyword": keyword,
            "language": language,
            "country": country,
            "results": [],
        }