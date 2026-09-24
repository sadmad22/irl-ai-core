from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import requests

from ..base import KeywordMetricsProvider, validate_keyword_metrics_response
from ...errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderResponseError,
)
from ...google_ads.config import (
    GOOGLE_ADS_API_VERSION,
    GOOGLE_ADS_BASE_URL,
    GOOGLE_ADS_CLIENT_ID,
    GOOGLE_ADS_CLIENT_SECRET,
    GOOGLE_ADS_CUSTOMER_ID,
    GOOGLE_ADS_DEVELOPER_TOKEN,
    GOOGLE_ADS_LANGUAGE_IDS,
    GOOGLE_ADS_LOCATION_IDS,
    GOOGLE_ADS_LOGIN_CUSTOMER_ID,
    GOOGLE_ADS_MAX_KEYWORDS_PER_REQUEST,
    GOOGLE_ADS_REFRESH_TOKEN,
    GOOGLE_ADS_TIMEOUT_SECONDS,
    GOOGLE_ADS_TOKEN_URL,
)

KEYWORD_HISTORICAL_METRICS_PATH = (
    "customers/{customer_id}:generateKeywordHistoricalMetrics"
)
OAUTH_SCOPE = "https://www.googleapis.com/auth/adwords"


class GoogleAdsKeywordMetricsProvider(KeywordMetricsProvider):
    """Google Ads historical keyword metrics provider behind the canonical boundary."""

    provider_name = "google_ads"

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        base_url: str | None = None,
        token_url: str | None = None,
        api_version: str | None = None,
        developer_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
        customer_id: str | None = None,
        login_customer_id: str | None = None,
        timeout_seconds: int | None = None,
        max_keywords_per_request: int | None = None,
        location_ids: dict[str, str] | None = None,
        language_ids: dict[str, str] | None = None,
        access_token: str | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.base_url = (base_url or GOOGLE_ADS_BASE_URL).rstrip("/")
        self.token_url = token_url or GOOGLE_ADS_TOKEN_URL
        self.api_version = (
            api_version or GOOGLE_ADS_API_VERSION
        ).strip().lower()
        self.developer_token = (
            developer_token
            if developer_token is not None
            else GOOGLE_ADS_DEVELOPER_TOKEN
        )
        self.client_id = client_id if client_id is not None else GOOGLE_ADS_CLIENT_ID
        self.client_secret = (
            client_secret
            if client_secret is not None
            else GOOGLE_ADS_CLIENT_SECRET
        )
        self.refresh_token = (
            refresh_token
            if refresh_token is not None
            else GOOGLE_ADS_REFRESH_TOKEN
        )
        self.customer_id = self._normalize_customer_id(
            customer_id if customer_id is not None else GOOGLE_ADS_CUSTOMER_ID,
            field="customer_id",
            required=True,
        )
        self.login_customer_id = self._normalize_customer_id(
            login_customer_id
            if login_customer_id is not None
            else GOOGLE_ADS_LOGIN_CUSTOMER_ID,
            field="login_customer_id",
            required=False,
        )
        self.timeout_seconds = (
            GOOGLE_ADS_TIMEOUT_SECONDS
            if timeout_seconds is None
            else timeout_seconds
        )
        self.max_keywords_per_request = (
            GOOGLE_ADS_MAX_KEYWORDS_PER_REQUEST
            if max_keywords_per_request is None
            else max_keywords_per_request
        )
        self.location_ids = dict(location_ids or GOOGLE_ADS_LOCATION_IDS)
        self.language_ids = dict(language_ids or GOOGLE_ADS_LANGUAGE_IDS)
        self._access_token = access_token

    @staticmethod
    def _normalize_customer_id(
        value: str | None,
        *,
        field: str,
        required: bool,
    ) -> str | None:
        if value is None or not str(value).strip():
            if required:
                raise ProviderConfigurationError(
                    f"Google Ads {field} is required.",
                    provider="google_ads",
                )
            return None

        normalized = str(value).replace("-", "").strip()
        if not normalized.isdigit():
            raise ProviderConfigurationError(
                f"Google Ads {field} must contain digits only.",
                provider="google_ads",
            )
        return normalized

    def _validate_configuration(self) -> None:
        if not self.base_url:
            raise ProviderConfigurationError(
                "Google Ads base URL is required.",
                provider=self.provider_name,
            )
        if not self.api_version:
            raise ProviderConfigurationError(
                "Google Ads API version is required.",
                provider=self.provider_name,
            )
        if not self.developer_token:
            raise ProviderConfigurationError(
                "Google Ads developer token is required.",
                provider=self.provider_name,
            )
        if self.timeout_seconds <= 0:
            raise ProviderConfigurationError(
                "Google Ads timeout must be positive.",
                provider=self.provider_name,
            )
        if self.max_keywords_per_request <= 0:
            raise ProviderConfigurationError(
                "Google Ads batch size must be positive.",
                provider=self.provider_name,
            )
        if self.max_keywords_per_request > 10000:
            raise ProviderConfigurationError(
                "Google Ads batch size cannot exceed 10000 keywords.",
                provider=self.provider_name,
            )

        if self._access_token:
            return

        missing = [
            name
            for name, value in (
                ("client_id", self.client_id),
                ("client_secret", self.client_secret),
                ("refresh_token", self.refresh_token),
            )
            if not value
        ]
        if missing:
            raise ProviderConfigurationError(
                "Google Ads OAuth configuration is incomplete: "
                + ", ".join(missing),
                provider=self.provider_name,
            )

    def _location_resource_name(self, country: str) -> str:
        key = country.strip().upper()
        location_id = self.location_ids.get(key)
        if location_id is None:
            raise ProviderConfigurationError(
                f"Unsupported Google Ads country: {key}",
                provider=self.provider_name,
            )
        return f"geoTargetConstants/{location_id}"

    def _language_resource_name(self, language: str) -> str:
        key = language.strip().lower()
        language_id = self.language_ids.get(key)
        if language_id is None:
            raise ProviderConfigurationError(
                f"Unsupported Google Ads language: {key}",
                provider=self.provider_name,
            )
        return f"languageConstants/{language_id}"

    def _refresh_access_token(self, *, force: bool = False) -> str:
        if self._access_token and not force:
            return self._access_token

        if not self.client_id or not self.client_secret or not self.refresh_token:
            raise ProviderConfigurationError(
                "Google Ads OAuth configuration is required to refresh the access token.",
                provider=self.provider_name,
            )

        try:
            response = self.session.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise ProviderNetworkError(
                "Google OAuth token request timed out.",
                provider=self.provider_name,
                cause=exc,
            ) from exc
        except requests.ConnectionError as exc:
            raise ProviderNetworkError(
                "Google OAuth token connection failed.",
                provider=self.provider_name,
                cause=exc,
            ) from exc
        except requests.RequestException as exc:
            raise ProviderNetworkError(
                "Google OAuth token request failed.",
                provider=self.provider_name,
                cause=exc,
            ) from exc

        if response.status_code in {400, 401, 403}:
            raise ProviderAuthenticationError(
                "Google Ads OAuth token exchange failed.",
                provider=self.provider_name,
            )
        if response.status_code == 429:
            raise ProviderRateLimitError(
                "Google OAuth token endpoint rate limit was reached.",
                provider=self.provider_name,
            )
        if response.status_code >= 400:
            raise ProviderResponseError(
                f"Google OAuth token endpoint returned HTTP {response.status_code}.",
                provider=self.provider_name,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderAuthenticationError(
                "Google OAuth token endpoint returned invalid JSON.",
                provider=self.provider_name,
                cause=exc,
            ) from exc

        token = payload.get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise ProviderAuthenticationError(
                "Google OAuth token response did not contain an access token.",
                provider=self.provider_name,
            )

        self._access_token = token.strip()
        return self._access_token

    def _request_historical_metrics(
        self,
        *,
        keywords: list[str],
        language: str,
        country: str,
    ) -> dict[str, Any]:
        if not keywords:
            raise ValueError("keywords must contain at least one non-empty keyword")

        if len(keywords) > self.max_keywords_per_request:
            raise ValueError(
                "keywords exceed the configured Google Ads batch size"
            )

        endpoint = (
            f"{self.base_url}/{self.api_version}/"
            + KEYWORD_HISTORICAL_METRICS_PATH.format(
                customer_id=self.customer_id
            )
        )

        request_body = {
            "customerId": self.customer_id,
            "keywords": keywords,
            "language": self._language_resource_name(language),
            "geoTargetConstants": [self._location_resource_name(country)],
            "keywordPlanNetwork": "GOOGLE_SEARCH",
            "historicalMetricsOptions": {"includeAverageCpc": True},
        }

        token = self._refresh_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "developer-token": self.developer_token or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.login_customer_id:
            headers["login-customer-id"] = self.login_customer_id

        try:
            response = self.session.post(
                endpoint,
                headers=headers,
                json=request_body,
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise ProviderNetworkError(
                "Google Ads historical metrics request timed out.",
                provider=self.provider_name,
                cause=exc,
            ) from exc
        except requests.ConnectionError as exc:
            raise ProviderNetworkError(
                "Google Ads historical metrics connection failed.",
                provider=self.provider_name,
                cause=exc,
            ) from exc
        except requests.RequestException as exc:
            raise ProviderNetworkError(
                "Google Ads historical metrics request failed.",
                provider=self.provider_name,
                cause=exc,
            ) from exc

        if response.status_code == 401:
            token = self._refresh_access_token(force=True)
            headers["Authorization"] = f"Bearer {token}"
            try:
                response = self.session.post(
                    endpoint,
                    headers=headers,
                    json=request_body,
                    timeout=self.timeout_seconds,
                )
            except requests.Timeout as exc:
                raise ProviderNetworkError(
                    "Google Ads retry request timed out.",
                    provider=self.provider_name,
                    cause=exc,
                ) from exc
            except requests.ConnectionError as exc:
                raise ProviderNetworkError(
                    "Google Ads retry connection failed.",
                    provider=self.provider_name,
                    cause=exc,
                ) from exc
            except requests.RequestException as exc:
                raise ProviderNetworkError(
                    "Google Ads retry request failed.",
                    provider=self.provider_name,
                    cause=exc,
                ) from exc

        if response.status_code in {401, 403}:
            raise ProviderAuthenticationError(
                "Google Ads authentication or authorization failed.",
                provider=self.provider_name,
            )
        if response.status_code == 429:
            raise ProviderRateLimitError(
                "Google Ads keyword planning rate limit was reached.",
                provider=self.provider_name,
            )
        if response.status_code >= 400:
            raise ProviderResponseError(
                self._response_error_message(response),
                provider=self.provider_name,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderResponseError(
                "Google Ads returned invalid JSON.",
                provider=self.provider_name,
                cause=exc,
            ) from exc

        if not isinstance(payload, dict):
            raise ProviderResponseError(
                "Google Ads returned an invalid response object.",
                provider=self.provider_name,
            )

        return payload

    @staticmethod
    def _response_error_message(response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return f"Google Ads returned HTTP {response.status_code}."

        if not isinstance(payload, dict):
            return f"Google Ads returned HTTP {response.status_code}."

        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return (
                    f"Google Ads returned HTTP {response.status_code}: "
                    + message.strip()
                )

        return f"Google Ads returned HTTP {response.status_code}."

    def _normalize_result(
        self,
        result: dict[str, Any],
        *,
        language: str,
        country: str,
    ) -> dict[str, Any]:
        keyword = result.get("text")
        metrics = result.get("keywordMetrics")
        if not isinstance(keyword, str) or not keyword.strip():
            raise ProviderResponseError(
                "Google Ads historical metrics result is missing text.",
                provider=self.provider_name,
            )
        if not isinstance(metrics, dict):
            raise ProviderResponseError(
                "Google Ads historical metrics result is missing keywordMetrics.",
                provider=self.provider_name,
            )

        avg_monthly_searches = self._integer_metric(
            metrics.get("avgMonthlySearches"),
            field="avgMonthlySearches",
        )
        competition_index = self._integer_metric(
            metrics.get("competitionIndex"),
            field="competitionIndex",
        )
        average_cpc_micros = self._integer_metric(
            metrics.get("averageCpcMicros"),
            field="averageCpcMicros",
        )

        monthly_volumes = metrics.get("monthlySearchVolumes", [])
        if not isinstance(monthly_volumes, list):
            raise ProviderResponseError(
                "Google Ads monthlySearchVolumes must be an array.",
                provider=self.provider_name,
            )

        trend: list[dict[str, int]] = []
        for volume in monthly_volumes:
            if not isinstance(volume, dict):
                raise ProviderResponseError(
                    "Google Ads monthly search volume must be an object.",
                    provider=self.provider_name,
                )
            year = self._integer_metric(volume.get("year"), field="year")
            month = self._integer_metric(volume.get("month"), field="month")
            monthly_searches = self._integer_metric(
                volume.get("monthlySearches"),
                field="monthlySearches",
            )
            trend.append(
                {
                    "year": year,
                    "month": month,
                    "search_volume": monthly_searches,
                }
            )

        normalized = {
            "provider": self.provider_name,
            "keyword": keyword.strip(),
            "search_volume": avg_monthly_searches,
            "competition": competition_index,
            "cpc": average_cpc_micros / 1_000_000,
            "trend": trend,
            "language": language.strip().lower(),
            "country": country.strip().upper(),
        }

        return validate_keyword_metrics_response(
            normalized,
            expected_provider=self.provider_name,
        )

    @staticmethod
    def _integer_metric(value: object, *, field: str) -> int:
        if isinstance(value, bool) or value is None:
            raise ProviderResponseError(
                f"Google Ads metric {field} is unavailable; no fallback value is allowed.",
                provider="google_ads",
            )
        try:
            integer_value = int(value)
        except (TypeError, ValueError) as exc:
            raise ProviderResponseError(
                f"Google Ads metric {field} is invalid.",
                provider="google_ads",
                cause=exc,
            ) from exc
        if integer_value < 0:
            raise ProviderResponseError(
                f"Google Ads metric {field} must be non-negative.",
                provider="google_ads",
            )
        return integer_value

    def get_metrics_batch(
        self,
        keywords: Iterable[str],
        language: str,
        country: str,
    ) -> list[dict[str, Any]]:
        self._validate_configuration()
        if not isinstance(language, str) or not language.strip():
            raise ValueError("language must be a non-empty string")
        if not isinstance(country, str) or not country.strip():
            raise ValueError("country must be a non-empty string")

        normalized_keywords: list[str] = []
        for keyword in keywords:
            if not isinstance(keyword, str) or not keyword.strip():
                raise ValueError("every keyword must be a non-empty string")
            normalized_keywords.append(keyword.strip())

        if not normalized_keywords:
            raise ValueError("keywords must contain at least one keyword")

        results: list[dict[str, Any]] = []
        for start in range(0, len(normalized_keywords), self.max_keywords_per_request):
            batch = normalized_keywords[
                start : start + self.max_keywords_per_request
            ]
            payload = self._request_historical_metrics(
                keywords=batch,
                language=language,
                country=country,
            )
            raw_results = payload.get("results")
            if not isinstance(raw_results, list):
                raise ProviderResponseError(
                    "Google Ads response is missing results.",
                    provider=self.provider_name,
                )

            for raw_result in raw_results:
                if not isinstance(raw_result, dict):
                    raise ProviderResponseError(
                        "Google Ads historical metrics result must be an object.",
                        provider=self.provider_name,
                    )
                results.append(
                    self._normalize_result(
                        raw_result,
                        language=language,
                        country=country,
                    )
                )

        return results

    def get_metrics(self, keyword: str, language: str, country: str) -> dict:
        if not isinstance(keyword, str) or not keyword.strip():
            raise ValueError("keyword must be a non-empty string")
        results = self.get_metrics_batch([keyword], language, country)
        if not results:
            raise ProviderResponseError(
                "Google Ads returned no historical metrics result for the keyword.",
                provider=self.provider_name,
            )
        return results[0]
