from agents.research import provider_config


def test_save_dataforseo_credentials_persists_and_sets_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(provider_config, "ENV_PATH", tmp_path / ".irl-ai-core.env")
    monkeypatch.delenv("DATAFORSEO_LOGIN", raising=False)
    monkeypatch.delenv("DATAFORSEO_PASSWORD", raising=False)
    monkeypatch.delenv("DATAFORSEO_BASE_URL", raising=False)

    provider_config.save_dataforseo_credentials("login-secret", "password-secret")

    saved = provider_config.ENV_PATH.read_text(encoding="utf-8")
    assert "DATAFORSEO_LOGIN=login-secret" in saved
    assert "DATAFORSEO_PASSWORD=password-secret" in saved
    assert provider_config.ENV_PATH.stat().st_mode & 0o777 == 0o600
    assert provider_config.os.getenv("DATAFORSEO_LOGIN") == "login-secret"
    assert provider_config.os.getenv("DATAFORSEO_PASSWORD") == "password-secret"


def test_save_wordpress_credentials_persists_and_sets_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(provider_config, "ENV_PATH", tmp_path / ".irl-ai-core.env")
    monkeypatch.delenv("WORDPRESS_BASE_URL", raising=False)
    monkeypatch.delenv("WORDPRESS_USERNAME", raising=False)
    monkeypatch.delenv("WORDPRESS_APPLICATION_PASSWORD", raising=False)

    provider_config.save_wordpress_credentials(
        "https://insurancereviewlab.com",
        "InsuranceReviewLab",
        "application-password-secret",
    )

    saved = provider_config.ENV_PATH.read_text(encoding="utf-8")
    assert "WORDPRESS_BASE_URL=https://insurancereviewlab.com" in saved
    assert "WORDPRESS_USERNAME=InsuranceReviewLab" in saved
    assert "WORDPRESS_APPLICATION_PASSWORD=application-password-secret" in saved
    assert provider_config.ENV_PATH.stat().st_mode & 0o777 == 0o600
    assert provider_config.wordpress_configuration_status()["configured"] is True


def test_load_saved_environment_does_not_override_existing_environment(tmp_path, monkeypatch):
    path = tmp_path / ".irl-ai-core.env"
    path.write_text("DATAFORSEO_LOGIN=file-login\nDATAFORSEO_PASSWORD=file-password\n", encoding="utf-8")
    monkeypatch.setattr(provider_config, "ENV_PATH", path)
    monkeypatch.setenv("DATAFORSEO_LOGIN", "shell-login")
    monkeypatch.delenv("DATAFORSEO_PASSWORD", raising=False)

    provider_config.load_saved_environment()

    assert provider_config.os.getenv("DATAFORSEO_LOGIN") == "shell-login"
    assert provider_config.os.getenv("DATAFORSEO_PASSWORD") == "file-password"


def test_wordpress_status_is_false_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(provider_config, "ENV_PATH", tmp_path / ".irl-ai-core.env")
    monkeypatch.delenv("WORDPRESS_BASE_URL", raising=False)
    monkeypatch.delenv("WORDPRESS_USERNAME", raising=False)
    monkeypatch.delenv("WORDPRESS_APPLICATION_PASSWORD", raising=False)
    assert provider_config.wordpress_configuration_status()["configured"] is False
