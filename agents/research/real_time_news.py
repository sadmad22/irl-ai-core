from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
LIFECYCLE_STAGE = "real_time_news_ready"
SOURCE = "news_api"


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _timestamp(value: Any, field: str) -> datetime:
    text = _text(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _id(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "news_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_real_time_news(*, article: dict[str, Any], outline_editor: dict[str, Any], news: dict[str, Any], as_of: str, max_items: int = 5, freshness_hours: int = 24) -> dict[str, Any]:
    if outline_editor.get("lifecycle_stage") != "outline_editor_ready":
        raise ValueError("Real-Time News requires outline_editor_ready")
    if not isinstance(max_items, int) or isinstance(max_items, bool) or not 1 <= max_items <= 20:
        raise ValueError("max_items must be between 1 and 20")
    if not isinstance(freshness_hours, int) or isinstance(freshness_hours, bool) or not 1 <= freshness_hours <= 168:
        raise ValueError("freshness_hours must be between 1 and 168")
    as_of_dt = _timestamp(as_of, "as_of")
    if news.get("source") != SOURCE or news.get("verified") is not True:
        raise ValueError("News evidence must be verified and sourced from news_api")
    items = news.get("items")
    if not isinstance(items, list):
        raise ValueError("news.items must be a list")
    _text(article.get("title"), "article.title")
    _text(article.get("content"), "article.content")
    lineage = {k: _text(outline_editor.get(k), f"outline_editor.{k}") for k in ("brief_id", "report_id", "decision_id", "strategy_id")}
    cutoff = as_of_dt - timedelta(hours=freshness_hours)
    selected = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("news.items[] must be an object")
        for key in ("news_id", "url", "title", "published_at", "summary", "relevance_score", "status"):
            if key not in item:
                raise ValueError(f"news.items[].{key} is required")
        if item["status"] != "verified":
            continue
        news_id = _text(item["news_id"], "news.items[].news_id")
        if news_id in seen:
            raise ValueError("news.items[].news_id must be unique")
        seen.add(news_id)
        url = _text(item["url"], "news.items[].url")
        if not url.startswith("https://"):
            raise ValueError("news.items[].url must use HTTPS")
        published = _timestamp(item["published_at"], "news.items[].published_at")
        if published < cutoff or published > as_of_dt:
            continue
        title = _text(item["title"], "news.items[].title")
        summary = _text(item["summary"], "news.items[].summary")
        score = item["relevance_score"]
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
            raise ValueError("news.items[].relevance_score must be between 0 and 1")
        selected.append({"news_id": news_id, "url": url, "title": title, "published_at": item["published_at"], "summary": summary, "relevance_score": score})
    selected.sort(key=lambda x: (-float(x["relevance_score"]), x["news_id"]))
    selected = selected[:max_items]
    payload = {"lineage": lineage, "as_of": as_of, "freshness_hours": freshness_hours, "items": selected, "schema_version": SCHEMA_VERSION, "method_version": METHOD_VERSION}
    return {"real_time_news_id": _id(payload), **lineage, "schema_version": SCHEMA_VERSION, "method_version": METHOD_VERSION, "lifecycle_stage": LIFECYCLE_STAGE, "as_of": as_of, "freshness_hours": freshness_hours, "items": selected, "audit": {"method": "verified_news_selection", "source": SOURCE, "validation_status": "validated"}}
