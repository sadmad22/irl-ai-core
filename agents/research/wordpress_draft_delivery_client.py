from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request

import requests


@dataclass(frozen=True)
class WordPressConnection:
    base_url: str
    username: str
    application_password: str
    timeout: float = 20.0

    @classmethod
    def from_env(cls) -> "WordPressConnection":
        base_url = os.getenv("WORDPRESS_BASE_URL", "").strip().rstrip("/")
        username = os.getenv("WORDPRESS_USERNAME", "").strip()
        password = os.getenv("WORDPRESS_APPLICATION_PASSWORD", "").strip()
        if not base_url or not username or not password:
            raise ValueError("WORDPRESS_BASE_URL, WORDPRESS_USERNAME and WORDPRESS_APPLICATION_PASSWORD are required")
        return cls(base_url=base_url, username=username, application_password=password)


def _endpoint(base_url: str) -> str:
    return base_url.rstrip("/") + "/wp-json/wp/v2/posts"


def _auth(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def _requests_sender(request: Request, timeout: float) -> Any:
    """Send the API request through Requests rather than urllib's default client."""
    response = requests.request(
        method=request.get_method(),
        url=request.full_url,
        data=request.data,
        headers=dict(request.header_items()),
        timeout=timeout,
    )
    response.raise_for_status()
    return response


def deliver_wordpress_draft(
    *,
    delivery: dict[str, Any],
    connection: WordPressConnection | None = None,
    transport: Callable[[Request, float], Any] | None = None,
) -> dict[str, Any]:
    """Create exactly one WordPress post as Draft. Never sends status=publish."""
    if delivery.get("platform") != "wordpress":
        raise ValueError("WordPress Draft Delivery requires platform=wordpress")
    if delivery.get("lifecycle_stage") != "wordpress_draft_ready":
        raise ValueError("WordPress Draft Delivery requires wordpress_draft_ready")
    payload = dict(delivery.get("request_payload") or {})
    if payload.get("status") != "draft":
        raise ValueError("WordPress Draft Delivery requires status=draft")
    if connection is None:
        connection = WordPressConnection.from_env()

    body = json.dumps({**payload, "status": "draft"}, ensure_ascii=False).encode("utf-8")
    request = Request(
        _endpoint(connection.base_url),
        data=body,
        method="POST",
        headers={
            "Authorization": _auth(connection.username, connection.application_password),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "curl/8.5.0 IRL-AI-Core/1.0",
        },
    )
    sender = transport or _requests_sender
    try:
        response = sender(request, connection.timeout)
        if hasattr(response, "content"):
         raw = response.content
        else:
         raw = response.read()

        data = json.loads(raw.decode("utf-8"))
    except (HTTPError, requests.HTTPError) as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status is None:
            status = getattr(exc, "code", "unknown")
        raise RuntimeError(f"WordPress draft delivery failed with HTTP {status}") from exc
    except (URLError, requests.RequestException, TimeoutError) as exc:
        raise RuntimeError("WordPress draft delivery connection failed") from exc

    if data.get("status") != "draft":
        raise RuntimeError("WordPress refused the immutable draft requirement")
    post_id = data.get("id")
    if not post_id:
        raise RuntimeError("WordPress response did not include a post id")
    return {
        "delivery_id": delivery["delivery_id"],
        "platform": "wordpress",
        "post_id": post_id,
        "status": "draft",
        "edit_url": data.get("link"),
        "remote_status": data.get("status"),
        "delivery_status": "delivered",
        "evidence_refs": list(delivery.get("evidence_refs", [])),
        "audit": {
            "method": "wordpress_draft_delivery_http",
            "version": "v1",
            "validation_status": "validated",
        },
    }
