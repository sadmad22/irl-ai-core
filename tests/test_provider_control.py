from agents.research.connectors.keyword_metrics.provider import get_provider as get_keyword_provider
from agents.research.connectors.serp.provider import get_provider as get_serp_provider
from scripts.web_ui import provider_status


def test_mock_provider_can_be_selected_per_run():
    assert get_keyword_provider("mock").__class__.__name__ == "MockKeywordMetricsProvider"
    assert get_serp_provider("mock").__class__.__name__ == "MockSERPProvider"


def test_provider_status_never_exposes_credentials(monkeypatch):
    monkeypatch.setenv("DATAFORSEO_LOGIN", "login-secret")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "password-secret")
    status = provider_status()
    assert status["dataforseo"]["configured"] is True
    rendered = str(status)
    assert "login-secret" not in rendered
    assert "password-secret" not in rendered
