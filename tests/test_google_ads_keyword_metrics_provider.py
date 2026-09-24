from __future__ import annotations

import pytest
import requests

from agents.research.connectors.errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderResponseError,
)
from agents.research.connectors.keyword_metrics.base import (
    validate_keyword_metrics_response,
)
from agents.research.connectors.keyword_metrics.provider import get_provider


class FakeResponse:
    def __init__(self, payload, *, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError("unexpected Google Ads request")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


VALID_PAYLOAD = {
    "results": [
        {
            "text": "expat health insurance",
            "keywordMetrics": {
                "avgMonthlySearches": "1200",
                "competition": "MEDIUM",
                "competitionIndex": "42",
                "averageCpcMicros": "2500000",
                "monthlySearchVolumes": [
                    {
                        "year": "2026",
                        "month": "SEPTEMBER",
                        "monthlySearches": "1400",
                    },
                    {
                        "year": "2026",
                        "month": "AUGUST",
                        "monthlySearches": "1000",
                    },
                ],
            },
        }
    ]
}


def make_provider(session, **overrides):
    from agents.research.connectors.keyword_metrics.providers.google_ads import (
        GoogleAdsKeywordMetricsProvider,
    )

    settings = {
        "session": session,
        "base_url": "https://googleads.example.test",
        "token_url": "https://oauth.example.test/token",
        "developer_token": "developer-token",
        "customer_id": "123-456-7890",
        "access_token": "access-token",
        "timeout_seconds": 9,
        "max_keywords_per_request": 10000,
    }
    settings.update(overrides)
    return GoogleAdsKeywordMetricsProvider(**settings)


def test_google_ads_provider_is_registered_independently():
    provider = get_provider("google_ads")
    assert provider.provider_name == "google_ads"


def test_google_ads_requires_runtime_credentials_before_network():
    session = FakeSession()
    provider = make_provider(
        session,
        access_token=None,
        developer_token=None,
    )
    with pytest.raises(ProviderConfigurationError):
        provider.get_metrics("kw", "en", "US")
    assert session.calls == []


def test_google_ads_normalizes_historical_metrics_without_faking_missing_fields():
    provider = make_provider(FakeSession(FakeResponse(VALID_PAYLOAD)))
    result = provider.get_metrics("expat health insurance", "EN", "us")

    validate_keyword_metrics_response(result, expected_provider="google_ads")
    assert result["provider"] == "google_ads"
    assert result["keyword"] == "expat health insurance"
    assert result["search_volume"] == 1200
    assert result["competition"] == 42
    assert result["cpc"] == 2.5
    assert result["trend"] == [
        {"year": 2026, "month": "SEPTEMBER", "search_volume": 1400},
        {"year": 2026, "month": "AUGUST", "search_volume": 1000},
    ]
    assert result["language"] == "en"
    assert result["country"] == "US"


def test_google_ads_request_maps_customer_language_country_network_and_average_cpc():
    session = FakeSession(FakeResponse(VALID_PAYLOAD))
    provider = make_provider(session, login_customer_id="999-888-7777")
    provider.get_metrics(" kw ", "EN", "us")

    url, kwargs = session.calls[0]
    assert url == (
        "https://googleads.example.test/v25/"
        "customers/1234567890:generateKeywordHistoricalMetrics"
    )
    assert kwargs["timeout"] == 9
    assert kwargs["headers"]["Authorization"] == "Bearer access-token"
    assert kwargs["headers"]["developer-token"] == "developer-token"
    assert kwargs["headers"]["login-customer-id"] == "9998887777"
    assert kwargs["json"] == {
        "customerId": "1234567890",
        "keywords": ["kw"],
        "language": "languageConstants/1000",
        "geoTargetConstants": ["geoTargetConstants/2840"],
        "keywordPlanNetwork": "GOOGLE_SEARCH",
        "historicalMetricsOptions": {"includeAverageCpc": True},
    }


def test_google_ads_oauth_refresh_uses_refresh_token_boundary_without_leaking_it():
    session = FakeSession(
        FakeResponse({"access_token": "fresh-access-token"}),
        FakeResponse(VALID_PAYLOAD),
    )
    provider = make_provider(
        session,
        access_token=None,
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="refresh-token",
    )

    provider.get_metrics("kw", "en", "US")

    token_url, token_kwargs = session.calls[0]
    assert token_url == "https://oauth.example.test/token"
    assert token_kwargs["data"] == {
        "client_id": "client-id",
        "client_secret": "client-secret",
        "grant_type": "refresh_token",
        "refresh_token": "refresh-token",
    }
    assert "refresh-token" not in session.calls[1][1]["headers"].get(
        "Authorization", ""
    )


def test_google_ads_unsupported_country_fails_closed_before_network():
    session = FakeSession()
    provider = make_provider(session)
    with pytest.raises(ProviderConfigurationError, match="Unsupported Google Ads country"):
        provider.get_metrics("kw", "en", "CA")
    assert session.calls == []


def test_google_ads_unsupported_language_fails_closed_before_network():
    session = FakeSession()
    provider = make_provider(session)
    with pytest.raises(ProviderConfigurationError, match="Unsupported Google Ads language"):
        provider.get_metrics("kw", "fr", "US")
    assert session.calls == []


def test_google_ads_missing_metric_fails_closed_instead_of_using_zero():
    payload = {
        "results": [
            {
                "text": "kw",
                "keywordMetrics": {
                    "avgMonthlySearches": "1200",
                    "competitionIndex": None,
                    "averageCpcMicros": "1000000",
                    "monthlySearchVolumes": [],
                },
            }
        ]
    }
    provider = make_provider(FakeSession(FakeResponse(payload)))
    with pytest.raises(ProviderResponseError, match="competitionIndex"):
        provider.get_metrics("kw", "en", "US")


@pytest.mark.parametrize("status", [401, 403])
def test_google_ads_authentication_errors_are_normalized(status):
    session = FakeSession(FakeResponse({}, status_code=status))
    provider = make_provider(session, client_id="c", client_secret="s", refresh_token="r")
    with pytest.raises(ProviderAuthenticationError):
        provider.get_metrics("kw", "en", "US")


def test_google_ads_rate_limit_error_is_normalized():
    provider = make_provider(FakeSession(FakeResponse({}, status_code=429)))
    with pytest.raises(ProviderRateLimitError):
        provider.get_metrics("kw", "en", "US")


def test_google_ads_http_error_is_normalized():
    response = FakeResponse(
        {"error": {"message": "invalid customer"}},
        status_code=400,
    )
    provider = make_provider(FakeSession(response))
    with pytest.raises(ProviderResponseError, match="invalid customer"):
        provider.get_metrics("kw", "en", "US")


def test_google_ads_invalid_json_is_normalized():
    class InvalidJsonResponse:
        status_code = 200

        def json(self):
            raise ValueError("invalid")

    provider = make_provider(FakeSession(InvalidJsonResponse()))
    with pytest.raises(ProviderResponseError, match="invalid JSON"):
        provider.get_metrics("kw", "en", "US")


def test_google_ads_oauth_network_failure_is_normalized():
    provider = make_provider(
        FakeSession(requests.Timeout("timeout")),
        access_token=None,
        client_id="c",
        client_secret="s",
        refresh_token="r",
    )
    with pytest.raises(ProviderNetworkError):
        provider.get_metrics("kw", "en", "US")


def test_google_ads_batching_splits_requests_and_preserves_normalized_results():
    payloads = [
        FakeResponse(
            {
                "results": [
                    {
                        "text": f"kw-{i}",
                        "keywordMetrics": {
                            "avgMonthlySearches": "100",
                            "competition": "LOW",
                            "competitionIndex": "20",
                            "averageCpcMicros": "1000000",
                            "monthlySearchVolumes": [],
                        },
                    }
                    for i in range(2)
                ]
            }
        ),
        FakeResponse(
            {
                "results": [
                    {
                        "text": "kw-2",
                        "keywordMetrics": {
                            "avgMonthlySearches": "200",
                            "competition": "HIGH",
                            "competitionIndex": "80",
                            "averageCpcMicros": "2000000",
                            "monthlySearchVolumes": [],
                        },
                    }
                ]
            }
        ),
    ]
    session = FakeSession(*payloads)
    provider = make_provider(session, max_keywords_per_request=2)

    results = provider.get_metrics_batch(
        ["kw-0", "kw-1", "kw-2"],
        "en",
        "US",
    )

    api_calls = [call for call in session.calls if "generateKeywordHistoricalMetrics" in call[0]]
    assert len(api_calls) == 2
    assert api_calls[0][1]["json"]["keywords"] == ["kw-0", "kw-1"]
    assert api_calls[1][1]["json"]["keywords"] == ["kw-2"]
    assert [item["keyword"] for item in results] == ["kw-0", "kw-1", "kw-2"]


def test_google_ads_batch_size_cannot_exceed_api_maximum():
    provider = make_provider(FakeSession(), max_keywords_per_request=10001)
    with pytest.raises(ProviderConfigurationError, match="10000"):
        provider.get_metrics("kw", "en", "US")
