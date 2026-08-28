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


def save_dataforseo_credentials(login: str, password: str, base_url: str | None = None) -> None:
    login = login.strip()
    password = password.strip()
    if not login or not password:
        raise ValueError("DataForSEO login and password are required")
    base_url = (base_url or os.getenv("DATAFORSEO_BASE_URL") or "https://api.dataforseo.com").strip().rstrip("/")
    if not base_url.startswith(("https://", "http://")):
        raise ValueError("DataForSEO base URL must use http:// or https://")
    content = "\n".join(
        [
            "# Local IRL AI Core provider credentials. Never commit this file.",
            f"DATAFORSEO_BASE_URL={base_url}",
            f"DATAFORSEO_LOGIN={login}",
            f"DATAFORSEO_PASSWORD={password}",
            "",
        ]
    )
    ENV_PATH.write_text(content, encoding="utf-8")
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass
    os.environ["DATAFORSEO_BASE_URL"] = base_url
    os.environ["DATAFORSEO_LOGIN"] = login
    os.environ["DATAFORSEO_PASSWORD"] = password


def saved_configuration_status() -> dict[str, bool]:
    load_saved_environment()
    return {
        "login_configured": bool(os.getenv("DATAFORSEO_LOGIN", "").strip()),
        "password_configured": bool(os.getenv("DATAFORSEO_PASSWORD", "").strip()),
    }
