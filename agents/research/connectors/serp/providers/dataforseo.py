import requests

from ..base import SERPProvider, validate_serp_response
from ..normalization import normalize_serp_url
from ...dataforseo.config import (
    DATAFORSEO_BASE_URL,
    DATAFORSEO_LOCATION_CODES,
    DATAFORSEO_LOGIN,
    DATAFORSEO_PASSWORD,
)
from ...errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderResponseError,
)

API_ENDPOINT = "/v3/serp/google/organic/live/advanced"


class DataForSEOSERPProvider(SERPProvider):
    """DataForSEO SERP provider behind the normalized SERP boundary."""

    provider_name = "dataforseo"

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        base_url: str | None = None,
        login: str | None = None,
        password: str | None = None,
        location_codes: dict[str, int] | None = None,
    ):
        self.session = session or requests.Session()
        self.base_url = (base_url or DATAFORSEO_BASE_URL).rstrip("/")
        self.login = login if login is not None else DATAFORSEO_LOGIN
        self.password = password if password is not None else DATAFORSEO_PASSWORD
        self.location_codes = dict(location_codes or DATAFORSEO_LOCATION_CODES)

    def get_results(self, keyword: str, language: str, country: str) -> dict:
        if not isinstance(keyword, str) or not keyword.strip():
            raise ValueError("keyword must be a non-empty string")
        if not isinstance(language, str) or not language.strip():
            raise ValueError("language must be a non-empty string")
        if not isinstance(country, str) or not country.strip():
            raise ValueError("country must be a non-empty string")

        if not self.base_url or not self.login or not self.password:
            raise ProviderConfigurationError(
                "DataForSEO credentials and base URL are required.",
                provider=self.provider_name,
            )
        if country not in self.location_codes:
            raise ProviderConfigurationError(
                f"Unsupported DataForSEO country: {country}",
                provider=self.provider_name,
            )

        try:
            response = self.session.post(
                self.base_url + API_ENDPOINT,
                auth=(self.login, self.password),
                json=[
                    {
                        "keyword": keyword.strip(),
                        "language_code": language.strip().lower(),
                        "location_code": self.location_codes[country],
                    }
                ],
            )
        except requests.Timeout as exc:
            raise ProviderNetworkError(
                "DataForSEO request timed out.",
                provider=self.provider_name,
                cause=exc,
            ) from exc
        except requests.ConnectionError as exc:
            raise ProviderNetworkError(
                "DataForSEO connection failed.",
                provider=self.provider_name,
                cause=exc,
            ) from exc
        except requests.RequestException as exc:
            raise ProviderNetworkError(
                "DataForSEO request failed.",
                provider=self.provider_name,
                cause=exc,
            ) from exc

        if response.status_code in {401, 403}:
            raise ProviderAuthenticationError(
                "DataForSEO authentication failed.",
                provider=self.provider_name,
            )
        if response.status_code == 429:
            raise ProviderRateLimitError(
                "DataForSEO rate limit was reached.",
                provider=self.provider_name,
            )
        if response.status_code >= 400:
            raise ProviderResponseError(
                f"DataForSEO returned HTTP {response.status_code}.",
                provider=self.provider_name,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderResponseError(
                "DataForSEO returned invalid JSON.",
                provider=self.provider_name,
                cause=exc,
            ) from exc

        try:
            task = data["tasks"][0]
            result_count = task["result_count"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderResponseError(
                "DataForSEO response is missing the expected task structure.",
                provider=self.provider_name,
                cause=exc,
            ) from exc

        results = []
        if result_count:
            try:
                items = task["result"][0]["items"]
            except (KeyError, IndexError, TypeError) as exc:
                raise ProviderResponseError(
                    "DataForSEO response is missing the expected result items.",
                    provider=self.provider_name,
                    cause=exc,
                ) from exc

            for item in items:
                if item.get("type") != "organic":
                    continue
                for field in ("title", "url", "domain", "description"):
                    if not isinstance(item.get(field), str):
                        raise ProviderResponseError(
                            f"DataForSEO organic result is missing {field}.",
                            provider=self.provider_name,
                        )
                results.append(
                    {
                        "position": len(results) + 1,
                        "title": item["title"],
                        "url": normalize_serp_url(item["url"]),
                        "domain": item["domain"],
                        "snippet": item["description"],
                    }
                )

        normalized = {
            "provider": self.provider_name,
            "keyword": keyword.strip(),
            "language": language.strip().lower(),
            "country": country.strip(),
            "position_semantics": "provider_order",
            "results": results,
        }
        return validate_serp_response(normalized, expected_provider=self.provider_name)
