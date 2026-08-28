from scripts import dashboard


def test_dashboard_html_is_available():
    assert "IRL AI Core Operations" in dashboard.OPERATIONS_HTML
    assert "Content Production" in dashboard.PRODUCTION_HTML
    assert "Production Console" in dashboard.PRODUCTION_HTML
    assert "DataForSEO Account &amp; Cost Monitor" in dashboard.OPERATIONS_HTML
    assert 'href="/provider"' in dashboard.OPERATIONS_HTML
    assert "Configure Provider" in dashboard.OPERATIONS_HTML
    assert "Manage DataForSEO" in dashboard.OPERATIONS_HTML
    assert "DataForSEO Configuration" in dashboard.PROVIDER_HTML
    assert "WordPress Configuration" in dashboard.PROVIDER_HTML
    assert "/api/providers/wordpress" in dashboard.PROVIDER_HTML


def test_dashboard_handler_reuses_proven_operator_backend():
    assert issubclass(dashboard.DashboardHandler, dashboard.web_ui.Handler)


def test_dashboard_provider_status_does_not_expose_credentials(monkeypatch):
    monkeypatch.setenv("DATAFORSEO_LOGIN", "login-secret")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "password-secret")
    status = dashboard.web_ui.provider_status()
    rendered = str(status)
    assert "login-secret" not in rendered
    assert "password-secret" not in rendered
