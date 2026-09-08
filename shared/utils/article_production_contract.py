from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
LIFECYCLE_STAGE = "production_ready"


def _production_id(*, article: dict[str, Any], quality: dict[str, Any]) -> str:
    raw = json.dumps(
        {
            "draft_id": article["draft_id"],
            "quality_id": quality["quality_id"],
            "schema_version": SCHEMA_VERSION,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return f"production_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_article_production(
    *,
    article: dict[str, Any],
    quality: dict[str, Any],
    optional_lineage: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the validated Core-to-WordPress production envelope."""
    required_article = ("draft_id", "brief_id", "report_id", "decision_id", "strategy_id")
    required_quality = ("quality_id", "draft_id", "brief_id", "report_id", "decision_id", "strategy_id")

    if not all(str(article.get(key, "")).strip() for key in required_article):
        raise ValueError("Article Draft lineage identifiers are required")
    if not all(str(quality.get(key, "")).strip() for key in required_quality):
        raise ValueError("Article Draft Quality lineage identifiers are required")
    if article.get("lifecycle_stage") != "draft_ready":
        raise ValueError("Article Draft must be draft_ready")
    if quality.get("lifecycle_stage") != "article_draft_quality_ready":
        raise ValueError("Article Draft Quality must be article_draft_quality_ready")
    if quality.get("outcome") != "passed":
        raise ValueError("Production requires a passed Article Draft Quality result")
    if quality.get("audit", {}).get("validation_status") != "validated":
        raise ValueError("Production requires validated Article Draft Quality")
    if quality.get("draft_id") != article.get("draft_id"):
        raise ValueError("Article Draft and Quality draft_id must match")

    lineage = {
        "report_id": str(article["report_id"]),
        "decision_id": str(article["decision_id"]),
        "strategy_id": str(article["strategy_id"]),
        "brief_id": str(article["brief_id"]),
        "draft_id": str(article["draft_id"]),
        "quality_id": str(quality["quality_id"]),
    }
    for key, value in (optional_lineage or {}).items():
        if value is not None and str(value).strip():
            lineage[str(key)] = str(value).strip()

    return {
        "production_id": _production_id(article=article, quality=quality),
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": LIFECYCLE_STAGE,
        "lineage": lineage,
        "article": article,
        "quality": quality,
        "publication": {
            "mode": "wordpress_draft",
            "publish": False,
            "human_approval_required": True,
        },
        "audit": {
            "method": "article_production_contract",
            "version": "v1",
            "validation_status": "validated",
        },
    }
