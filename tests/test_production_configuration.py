from __future__ import annotations

import pytest

from agents.research.connectors.errors import ProviderConfigurationError
from agents.research.connectors.keyword_metrics.provider import (
    get_provider as get_keyword_metrics_provider,
)
from agents.research.connectors.serp.provider import get_provider as get_serp_provider


def test_production_serp_default_is_brave(monkeypatch):
    import agents.research.connectors.serp.config as config

    monkeypatch.setattr(config, "SERP_PROVIDER", "brave")
    assert get_serp_provider().provider_name == "brave"


def test_production_keyword_metrics_default_is_google_ads(monkeypatch):
    import agents.research.connectors.keyword_metrics.config as config

    monkeypatch.setattr(config, "KEYWORD_METRICS_PROVIDER", "google_ads")
    assert get_keyword_metrics_provider().provider_name == "google_ads"


@pytest.mark.parametrize("provider_name", ["mock", "dataforseo"])
def test_production_serp_rejects_legacy_provider(monkeypatch, provider_name):
    monkeypatch.setenv("IRL_ENVIRONMENT", "production")

    with pytest.raises(ProviderConfigurationError, match="must be brave"):
        get_serp_provider(provider_name)


@pytest.mark.parametrize("provider_name", ["mock", "dataforseo"])
def test_production_keyword_metrics_rejects_legacy_provider(
    monkeypatch,
    provider_name,
):
    monkeypatch.setenv("IRL_ENVIRONMENT", "production")

    with pytest.raises(ProviderConfigurationError, match="must be google_ads"):
        get_keyword_metrics_provider(provider_name)


def test_production_brave_fails_closed_without_credentials(monkeypatch):
    monkeypatch.setenv("IRL_ENVIRONMENT", "production")
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)

    from agents.research.connectors.serp.providers.brave import BraveSERPProvider

    provider = BraveSERPProvider(api_key=None)

    with pytest.raises(ProviderConfigurationError, match="API key"):
        provider.get_results("kw", "en", "US")


def test_production_google_ads_fails_closed_without_credentials(monkeypatch):
    monkeypatch.setenv("IRL_ENVIRONMENT", "production")
    monkeypatch.delenv("GOOGLE_ADS_DEVELOPER_TOKEN", raising=False)
    monkeypatch.delenv("GOOGLE_ADS_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_ADS_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GOOGLE_ADS_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("GOOGLE_ADS_CUSTOMER_ID", raising=False)

    from agents.research.connectors.keyword_metrics.providers.google_ads import (
        GoogleAdsKeywordMetricsProvider,
    )

    provider = GoogleAdsKeywordMetricsProvider(
        developer_token=None,
        customer_id=None,
        access_token=None,
        client_id=None,
        client_secret=None,
        refresh_token=None,
    )

    with pytest.raises(ProviderConfigurationError):
        provider.get_metrics("kw", "en", "US")
