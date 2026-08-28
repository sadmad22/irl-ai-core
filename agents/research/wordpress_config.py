from __future__ import annotations

import base64
from typing import Any

import requests


def verify_wordpress_credentials(base_url: str, username: str, application_password: str) -> dict[str, Any]:
    base_url = base_url.strip().rstrip("/")
    username = username.strip()
    application_password = application_password.strip()
    if not base_url or not username or not application_password:
        raise ValueError("WordPress base URL, username and application password are required")
    if not base_url.startswith(("https://", "http://")):
        raise ValueError("WordPress base URL must use http:// or https://")
    token = base64.b64encode(f"{username}:{application_password}".encode()).decode()
    response = requests.get(
        f"{base_url}/wp-json/wp/v2/users/me",
        headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
        timeout=15,
    )
    if response.status_code >= 400:
        return {"verified": False, "status_code": response.status_code}
    try:
        data = response.json()
    except ValueError:
        return {"verified": False, "status_code": response.status_code}
    return {
        "verified": bool(data.get("id")),
        "status_code": response.status_code,
        "user_id": data.get("id"),
    }
