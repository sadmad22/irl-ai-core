from ..base import SERPProvider, validate_serp_response


class MockSERPProvider(SERPProvider):
    """Explicit mock provider for contract and unit tests."""

    provider_name = "mock"

    def get_results(self, keyword: str, language: str, country: str) -> dict:
        payload = {
            "provider": self.provider_name,
            "keyword": keyword,
            "language": language,
            "country": country,
            "position_semantics": "provider_order",
            "results": [],
        }
        return validate_serp_response(payload, expected_provider=self.provider_name)
