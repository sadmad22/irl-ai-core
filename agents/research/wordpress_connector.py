from __future__ import annotations

import hashlib
import html
import json
import re
from typing import Any, Callable

from .wordpress_draft_delivery_client import WordPressConnection, deliver_wordpress_draft

SCHEMA_VERSION = "1.0"
LIFECYCLE_STAGE = "wordpress_connector_ready"


def _connector_id(production_id: str) -> str:
    raw = json.dumps({"production_id": production_id, "schema_version": SCHEMA_VERSION}, sort_keys=True)
    return f"wpconn_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _article_content(article: dict[str, Any]) -> str:
    parts: list[str] = []
    for section in article.get("sections", []):
        heading = str(section.get("heading", "")).strip()
        body = str(section.get("body", "")).strip()
        if heading:
            parts.append(f"<h2>{html.escape(heading)}</h2>")
        if body:
            parts.append(body)
    return "\n\n".join(parts)


def build_wordpress_connector_request(production: dict[str, Any]) -> dict[str, Any]:
    """Map a validated Article Production Contract to a WordPress Draft request."""
    if not isinstance(production, dict):
        raise TypeError("production must be a dictionary")
    if production.get("lifecycle_stage") != "production_ready":
        raise ValueError("WordPress Connector requires production_ready")
    publication = production.get("publication")
    if not isinstance(publication, dict):
        raise ValueError("Article Production publication intent is required")
    if publication.get("mode") != "wordpress_draft":
        raise ValueError("WordPress Connector requires publication.mode=wordpress_draft")
    if publication.get("publish") is not False:
        raise ValueError("WordPress Connector requires publish=false")
    if publication.get("human_approval_required") is not True:
        raise ValueError("WordPress Connector requires human approval")

    production_id = str(production.get("production_id", "")).strip()
    if not re.fullmatch(r"production_[a-f0-9]{16}", production_id):
        raise ValueError("production_id must match ^production_[a-f0-9]{16}$")
    article = production.get("article")
    if not isinstance(article, dict):
        raise ValueError("Article Production article is required")
    title = str(article.get("title", "")).strip()
    content = _article_content(article)
    if not title or not content:
        raise ValueError("Article title and content are required")

    return {
        "connector_id": _connector_id(production_id),
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": LIFECYCLE_STAGE,
        "platform": "wordpress",
        "operation": "create_draft",
        "source": {"production_id": production_id},
        "request_payload": {"title": title, "content": content, "status": "draft"},
        "audit": {"method": "wordpress_connector", "version": "v1", "validation_status": "validated"},
    }


def deliver_wordpress_draft_from_production(
    production: dict[str, Any],
    *,
    connection: WordPressConnection | None = None,
    transport: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Deliver a validated Article Production Contract as a WordPress Draft."""
    connector = build_wordpress_connector_request(production)
    delivery = {
        "delivery_id": connector["connector_id"],
        "platform": "wordpress",
        "lifecycle_stage": "wordpress_draft_ready",
        "request_payload": connector["request_payload"],
        "evidence_refs": [connector["source"]["production_id"]],
    }
    result = deliver_wordpress_draft(
        delivery=delivery,
        connection=connection,
        transport=transport,
    )

    connector["response"] = {
        "delivery_status": "delivered",
        "post_id": result["post_id"],
        "edit_url": result.get("edit_url"),
        "remote_status": "draft",
        "error": None,
    }
    return connector
