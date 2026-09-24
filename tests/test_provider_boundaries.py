import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.connectors.errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
)
from agents.research.connectors.keyword_metrics.base import (
    validate_keyword_metrics_response,
)
from agents.research.connectors.keyword_metrics.provider import (
    get_provider as get_keyword_metrics_provider,
)
from agents.research.connectors.serp.base import validate_serp_response
from agents.research.connectors.serp.provider import (
    get_provider as get_serp_provider,
)
from agents.research.connectors.serp.providers.dataforseo import (
    DataForSEOSERPProvider,
)
from agents.research.connectors.keyword_metrics.providers.dataforseo import (
    DataForSEOKeywordMetricsProvider,
)


ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_serp_factory_is_capability_specific_and_unknown_provider_fails(monkeypatch):
    import agents.research.connectors.serp.provider as module

    monkeypatch.setattr(module, "SERP_PROVIDER", "mock")
    provider = get_serp_provider()
    assert provider.provider_name == "mock"

    with pytest.raises(ValueError, match="Unsupported SERP provider"):
        get_serp_provider("unknown")


def test_keyword_metrics_factory_is_independent_and_unknown_provider_fails(monkeypatch):
    import agents.research.connectors.keyword_metrics.provider as module

    monkeypatch.setattr(module, "KEYWORD_METRICS_PROVIDER", "mock")
    provider = get_keyword_metrics_provider()
    assert provider.provider_name == "mock"

    with pytest.raises(ValueError, match="Unsupported keyword metrics provider"):
        get_keyword_metrics_provider("unknown")


def test_serp_mock_response_matches_strict_provider_contract():
    response = get_serp_provider("mock").get_results(
        keyword="expat health insurance",
        language="en",
        country="US",
    )
    validate_serp_response(response, expected_provider="mock")
    schema = json.loads(
        (ROOT / "shared/schemas/serp-provider-response.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(response)


def test_keyword_metrics_mock_response_matches_strict_provider_contract():
    response = get_keyword_metrics_provider("mock").get_metrics(
        keyword="expat health insurance",
        language="en",
        country="US",
    )
    validate_keyword_metrics_response(response, expected_provider="mock")
    schema = json.loads(
        (ROOT / "shared/schemas/keyword-metrics-provider-response.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(response)


def test_serp_contract_rejects_google_rank_semantics():
    response = {
        "provider": "mock",
        "keyword": "kw",
        "language": "en",
        "country": "US",
        "position_semantics": "google_rank",
        "results": [],
    }
    with pytest.raises(ValueError, match="position semantics"):
        validate_serp_response(response)


def test_keyword_metrics_contract_rejects_legacy_difficulty_only():
    response = {
        "provider": "mock",
        "keyword": "kw",
        "search_volume": 100,
        "difficulty": 35,
        "cpc": 1.0,
        "trend": [],
        "language": "en",
        "country": "US",
    }
    with pytest.raises(ValueError, match="missing fields"):
        validate_keyword_metrics_response(response)


def test_dataforseo_serp_normalizes_provider_order_and_country_mapping():
    response = FakeResponse(
        {
            "tasks": [
                {
                    "result_count": 1,
                    "result": [
                        {
                            "items": [
                                {
                                    "type": "paid",
                                    "rank_absolute": 1,
                                    "title": "Ad",
                                    "url": "https://ads.example.com",
                                    "domain": "ads.example.com",
                                    "description": "ad",
                                },
                                {
                                    "type": "organic",
                                    "rank_absolute": 7,
                                    "title": "Result one",
                                    "url": "https://example.com/page?utm_source=x",
                                    "domain": "example.com",
                                    "description": "One",
                                },
                                {
                                    "type": "organic",
                                    "rank_absolute": 9,
                                    "title": "Result two",
                                    "url": "https://example.org/page",
                                    "domain": "example.org",
                                    "description": "Two",
                                },
                            ]
                        }
                    ],
                }
            ]
        }
    )
    session = FakeSession(response)
    provider = DataForSEOSERPProvider(
        session=session,
        base_url="https://api.example.test",
        login="login",
        password="password",
        location_codes={"US": 999},
    )
    result = provider.get_results("kw", "en", "US")

    assert result["provider"] == "dataforseo"
    assert result["position_semantics"] == "provider_order"
    assert [item["position"] for item in result["results"]] == [1, 2]
    assert result["results"][0]["url"] == "https://example.com/page"

    payload = session.calls[0][1]["json"][0]
    assert payload["location_code"] == 999


def test_dataforseo_keyword_metrics_uses_canonical_competition_field():
    response = FakeResponse(
        {
            "tasks": [
                {
                    "result_count": 1,
                    "result": [
                        {
                            "keyword": "kw",
                            "search_volume": 1300,
                            "competition_index": 18,
                            "cpc": 19.35,
                            "monthly_searches": [],
                            "language_code": "en",
                        }
                    ],
                }
            ]
        }
    )
    session = FakeSession(response)
    provider = DataForSEOKeywordMetricsProvider(
        session=session,
        base_url="https://api.example.test",
        login="login",
        password="password",
        location_codes={"US": 999},
    )
    result = provider.get_metrics("kw", "en", "US")

    assert result["provider"] == "dataforseo"
    assert result["competition"] == 18
    assert "difficulty" not in result

    payload = session.calls[0][1]["json"][0]
    assert payload["location_code"] == 999


def test_dataforseo_missing_credentials_fail_closed_before_network():
    session = FakeSession(FakeResponse({}))
    provider = DataForSEOKeywordMetricsProvider(
        session=session,
        base_url="https://api.example.test",
        login=None,
        password=None,
    )
    with pytest.raises(ProviderConfigurationError):
        provider.get_metrics("kw", "en", "US")
    assert session.calls == []


def test_dataforseo_authentication_error_is_normalized():
    provider = DataForSEOSERPProvider(
        session=FakeSession(FakeResponse({}, status_code=401)),
        base_url="https://api.example.test",
        login="login",
        password="password",
        location_codes={"US": 999},
    )
    with pytest.raises(ProviderAuthenticationError):
        provider.get_results("kw", "en", "US")
