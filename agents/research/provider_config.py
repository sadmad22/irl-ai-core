from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".irl-ai-core.env"


def _parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def load_saved_environment() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    try:
        values = _parse_env(ENV_PATH.read_text(encoding="utf-8"))
    except OSError:
        return {}
    for key, value in values.items():
        if value and not os.getenv(key):
            os.environ[key] = value
    return values


def _write_values(updates: dict[str, str]) -> None:
    existing = {}
    if ENV_PATH.exists():
        try:
            existing = _parse_env(ENV_PATH.read_text(encoding="utf-8"))
        except OSError:
            existing = {}
    existing.update({key: value for key, value in updates.items() if value != ""})
    lines = ["# Local IRL AI Core provider credentials. Never commit this file."]
    lines.extend(f"{key}={value}" for key, value in sorted(existing.items()))
    lines.append("")
    ENV_PATH.write_text("\n".join(lines), encoding="utf-8")
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass
    for key, value in updates.items():
        if value:
            os.environ[key] = value


def save_dataforseo_credentials(login: str, password: str, base_url: str | None = None) -> None:
    login = login.strip()
    password = password.strip()
    if not login or not password:
        raise ValueError("DataForSEO login and password are required")
    base_url = (base_url or os.getenv("DATAFORSEO_BASE_URL") or "https://api.dataforseo.com").strip().rstrip("/")
    if not base_url.startswith(("https://", "http://")):
        raise ValueError("DataForSEO base URL must use http:// or https://")
    _write_values({
        "DATAFORSEO_BASE_URL": base_url,
        "DATAFORSEO_LOGIN": login,
        "DATAFORSEO_PASSWORD": password,
    })


def save_wordpress_credentials(base_url: str, username: str, application_password: str) -> None:
    base_url = base_url.strip().rstrip("/")
    username = username.strip()
    application_password = application_password.strip()
    if not base_url or not username or not application_password:
        raise ValueError("WordPress base URL, username and application password are required")
    if not base_url.startswith(("https://", "http://")):
        raise ValueError("WordPress base URL must use http:// or https://")
    _write_values({
        "WORDPRESS_BASE_URL": base_url,
        "WORDPRESS_USERNAME": username,
        "WORDPRESS_APPLICATION_PASSWORD": application_password,
    })


def saved_configuration_status() -> dict[str, bool]:
    load_saved_environment()
    return {
        "login_configured": bool(os.getenv("DATAFORSEO_LOGIN", "").strip()),
        "password_configured": bool(os.getenv("DATAFORSEO_PASSWORD", "").strip()),
    }


def wordpress_configuration_status() -> dict[str, bool]:
    load_saved_environment()
    return {
        "base_url_configured": bool(os.getenv("WORDPRESS_BASE_URL", "").strip()),
        "username_configured": bool(os.getenv("WORDPRESS_USERNAME", "").strip()),
        "application_password_configured": bool(os.getenv("WORDPRESS_APPLICATION_PASSWORD", "").strip()),
        "configured": all(
            bool(os.getenv(key, "").strip())
            for key in (
                "WORDPRESS_BASE_URL",
                "WORDPRESS_USERNAME",
                "WORDPRESS_APPLICATION_PASSWORD",
            )
        ),
    }
