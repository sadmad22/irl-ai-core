from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

ARTICLE_TYPES = {"guide", "comparison", "buyer_guide", "article"}
ARTICLE_SIZES = {"short", "standard", "long"}

# Conservative editorial defaults. They are explicit policy, not SEO claims.
SIZE_DEFAULTS = {
    "short": {"words": {"min": 800, "target": 1200, "max": 1600}, "h2": {"min": 4, "target": 6, "max": 8}, "h3": {"min": 2, "target": 4, "max": 6}},
    "standard": {"words": {"min": 1400, "target": 2000, "max": 2600}, "h2": {"min": 6, "target": 8, "max": 10}, "h3": {"min": 4, "target": 7, "max": 10}},
    "long": {"words": {"min": 2200, "target": 3000, "max": 4000}, "h2": {"min": 8, "target": 11, "max": 14}, "h3": {"min": 6, "target": 10, "max": 14}},
}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _target(value: Any, field: str, *, minimum_allowed: int = 0) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    minimum = _positive_int(value.get("min"), f"{field}.min")
    target = _positive_int(value.get("target"), f"{field}.target")
    maximum = _positive_int(value.get("max"), f"{field}.max")
    if minimum < minimum_allowed:
        raise ValueError(f"{field}.min must be at least {minimum_allowed}")
    if not minimum <= target <= maximum:
        raise ValueError(f"{field} must satisfy min <= target <= max")
    return {"min": minimum, "target": target, "max": maximum}


def _config_id(brief_id: str, payload: dict[str, Any]) -> str:
    raw = json.dumps({"brief_id": brief_id, "configuration": payload}, sort_keys=True, ensure_ascii=False)
    return f"config_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_article_config(*, content_brief: dict[str, Any], target_country: str, article_size: str = "standard", word_target: dict[str, int] | None = None, heading_target: dict[str, int] | None = None) -> dict[str, Any]:
    """Build the P0 Article Config Engine contract from a ready Content Brief.

    The engine selects the article type from the brief, applies an explicit size
    profile, and requires an explicit target country. Word/heading targets may
    override the profile while remaining range-valid.
    """
    if not isinstance(content_brief, dict):
        raise ValueError("content_brief must be an object")
    lineage = {key: _text(content_brief.get(key), key) for key in ("brief_id", "report_id", "decision_id", "strategy_id")}
    if content_brief.get("lifecycle_stage") != "content_brief_ready":
        raise ValueError("Article Config requires a content_brief_ready Content Brief")

    article_type = _text(content_brief.get("content_type"), "content_type")
    if article_type not in ARTICLE_TYPES:
        raise ValueError("content_type must be one of the supported article types")
    country = _text(target_country, "target_country")
    size = _text(article_size, "article_size").lower()
    if size not in ARTICLE_SIZES:
        raise ValueError("article_size must be one of: short, standard, long")

    defaults = SIZE_DEFAULTS[size]
    words = _target(word_target if word_target is not None else defaults["words"], "word_target", minimum_allowed=1)
    headings = _target(heading_target if heading_target is not None else defaults["h2"], "heading_target", minimum_allowed=1)
    h3_target = dict(defaults["h3"])

    payload = {
        **lineage,
        "article_type": article_type,
        "article_size": size,
        "target_country": country,
        "word_target": words,
        "heading_target": headings,
        "h3_target": h3_target,
    }
    return {
        "config_id": _config_id(lineage["brief_id"], payload),
        "brief_id": lineage["brief_id"],
        "report_id": lineage["report_id"],
        "decision_id": lineage["decision_id"],
        "strategy_id": lineage["strategy_id"],
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "article_config_ready",
        "article_type": article_type,
        "article_size": size,
        "target_country": country,
        "word_target": words,
        "heading_target": headings,
        "h3_target": h3_target,
        "audit": {
            "method": "content_brief_to_article_config_engine",
            "version": METHOD_VERSION,
            "validation_status": "validated",
            "target_policy": "explicit_country_required",
        },
    }
