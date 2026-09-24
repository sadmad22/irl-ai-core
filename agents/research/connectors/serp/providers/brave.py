from __future__ import annotations

from urllib.parse import urlsplit

import requests

from ..base import SERPProvider, validate_serp_response
from ..normalization import normalize_serp_url
from ...brave.config import (
    BRAVE_SEARCH_API_KEY,
    BRAVE_SEARCH_BASE_URL,
    BRAVE_SEARCH_COUNT,
    BRAVE_SEARCH_FRESHNESS,
    BRAVE_SEARCH_OFFSET,
    BRAVE_SEARCH_TIMEOUT_SECONDS,
)
from ...errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderResponseError,
)


class BraveSERPProvider(SERPProvider):
    """Brave Web Search provider behind the canonical SERP boundary."""

    provider_name = "brave"

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        count: int | None = None,
        offset: int | None = None,
        freshness: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.base_url = (base_url or BRAVE_SEARCH_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else BRAVE_SEARCH_API_KEY
        self.count = BRAVE_SEARCH_COUNT if count is None else count
        self.offset = BRAVE_SEARCH_OFFSET if offset is None else offset
        self.freshness = (
            BRAVE_SEARCH_FRESHNESS if freshness is None else freshness.strip()
        )
        self.timeout_seconds = (
            BRAVE_SEARCH_TIMEOUT_SECONDS
            if timeout_seconds is None
            else timeout_seconds
        )

    @staticmethod
    def _validate_search_limits(*, count: int, offset: int) -> None:
        if not 1 <= count <= 20:
            raise ValueError("Brave Search count must be between 1 and 20")
        if not 0 <= offset <= 9:
            raise ValueError("Brave Search offset must be between 0 and 9")

    def _search_page(
        self,
        *,
        keyword: str,
        language: str,
        country: str,
        count: int,
        offset: int,
    ) -> dict:
        self._validate_search_limits(count=count, offset=offset)

        params = {
            "q": keyword.strip(),
            "country": country.strip().upper(),
            "search_lang": language.strip().lower(),
            "count": count,
            "offset": offset,
        }
        if self.freshness:
            params["freshness"] = self.freshness

        try:
            response = self.session.get(
                self.base_url,
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self.api_key or "",
                },
                params=params,
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise ProviderNetworkError(
                "Brave Search request timed out.",
                provider=self.provider_name,
                cause=exc,
            ) from exc
        except requests.ConnectionError as exc:
            raise ProviderNetworkError(
                "Brave Search connection failed.",
                provider=self.provider_name,
                cause=exc,
            ) from exc
        except requests.RequestException as exc:
            raise ProviderNetworkError(
                "Brave Search request failed.",
                provider=self.provider_name,
                cause=exc,
            ) from exc

        if response.status_code in {401, 403}:
            raise ProviderAuthenticationError(
                "Brave Search authentication failed.",
                provider=self.provider_name,
            )
        if response.status_code == 429:
            raise ProviderRateLimitError(
                "Brave Search rate limit was reached.",
                provider=self.provider_name,
            )
        if response.status_code >= 400:
            raise ProviderResponseError(
                f"Brave Search returned HTTP {response.status_code}.",
                provider=self.provider_name,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderResponseError(
                "Brave Search returned invalid JSON.",
                provider=self.provider_name,
                cause=exc,
            ) from exc

        if not isinstance(payload, dict):
            raise ProviderResponseError(
                "Brave Search returned an invalid response object.",
                provider=self.provider_name,
            )

        return payload

    def get_results(self, keyword: str, language: str, country: str) -> dict:
        if not isinstance(keyword, str) or not keyword.strip():
            raise ValueError("keyword must be a non-empty string")
        if not isinstance(language, str) or not language.strip():
            raise ValueError("language must be a non-empty string")
        if not isinstance(country, str) or not country.strip():
            raise ValueError("country must be a non-empty string")
        if not self.base_url or not self.api_key:
            raise ProviderConfigurationError(
                "Brave Search API key and base URL are required.",
                provider=self.provider_name,
            )
        if self.timeout_seconds <= 0:
            raise ProviderConfigurationError(
                "Brave Search timeout must be positive.",
                provider=self.provider_name,
            )

        payload = self._search_page(
            keyword=keyword,
            language=language,
            country=country,
            count=self.count,
            offset=self.offset,
        )

        web = payload.get("web")
        if not isinstance(web, dict):
            raise ProviderResponseError(
                "Brave Search response is missing the web result collection.",
                provider=self.provider_name,
            )

        raw_results = web.get("results")
        if not isinstance(raw_results, list):
            raise ProviderResponseError(
                "Brave Search response is missing web.results.",
                provider=self.provider_name,
            )

        results: list[dict[str, object]] = []
        for item in raw_results:
            if not isinstance(item, dict):
                raise ProviderResponseError(
                    "Brave Search returned a non-object web result.",
                    provider=self.provider_name,
                )

            title = item.get("title")
            url = item.get("url")
            snippet = item.get("description")
            if not all(isinstance(value, str) and value.strip() for value in (title, url, snippet)):
                raise ProviderResponseError(
                    "Brave Search web result is missing title, url, or description.",
                    provider=self.provider_name,
                )

            hostname = urlsplit(url).hostname
            if not hostname:
                raise ProviderResponseError(
                    "Brave Search web result URL is missing a hostname.",
                    provider=self.provider_name,
                )

            results.append(
                {
                    "position": len(results) + 1,
                    "title": title,
                    "url": normalize_serp_url(url),
                    "domain": hostname.lower(),
                    "snippet": snippet,
                }
            )

        normalized = {
            "provider": self.provider_name,
            "keyword": keyword.strip(),
            "language": language.strip().lower(),
            "country": country.strip().upper(),
            "position_semantics": "provider_order",
            "results": results,
        }
        return validate_serp_response(
            normalized,
            expected_provider=self.provider_name,
        )
