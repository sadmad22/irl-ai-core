from __future__ import annotations

import hashlib
import json
from typing import Any

from .analyzers.competitor import analyze_competitors
from .connectors.serp.base import SERPProvider

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _lineage(source: dict[str, Any]) -> dict[str, str]:
    return {
        key: _text(source.get(key), key)
        for key in ("brief_id", "report_id", "decision_id", "strategy_id")
    }


def _analysis_id(lineage: dict[str, str], keyword: str, language: str, country: str, serp: dict[str, Any]) -> str:
    raw = json.dumps(
        {
            "lineage": lineage,
            "keyword": keyword,
            "language": language,
            "country": country,
            "serp": serp,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return f"serp_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_serp_analysis(
    *,
    content_strategy: dict[str, Any],
    article_config: dict[str, Any],
    provider: SERPProvider,
    language: str = "en",
) -> dict[str, Any]:
    """Build a real-time SERP + competitor analysis contract.

    The layer consumes the existing Content Strategy and Article Config
    contracts, calls the injected SERP provider, and feeds its normalized
    results into the existing competitor analyzer. No provider is created
    implicitly, which keeps network access explicit and testable.
    """
    if not isinstance(content_strategy, dict):
        raise ValueError("content_strategy must be an object")
    if not isinstance(article_config, dict):
        raise ValueError("article_config must be an object")
    if not isinstance(provider, SERPProvider):
        raise ValueError("provider must implement SERPProvider")

    if content_strategy.get("lifecycle_stage") != "content_strategy_ready":
        raise ValueError("SERP Analysis requires a content_strategy_ready Content Strategy")
    if article_config.get("lifecycle_stage") != "article_config_ready":
        raise ValueError("SERP Analysis requires an article_config_ready Article Config")

    strategy_lineage = _lineage(content_strategy)
    config_lineage = _lineage(article_config)
    if strategy_lineage != config_lineage:
        raise ValueError("Content Strategy and Article Config lineage must match")

    keyword = _text(content_strategy.get("primary_keyword"), "primary_keyword")
    country = _text(article_config.get("target_country"), "target_country")
    language = _text(language, "language").lower()

    serp = provider.get_results(keyword=keyword, language=language, country=country)
    if not isinstance(serp, dict):
        raise ValueError("SERP provider must return an object")

    required = {"keyword", "language", "country", "results"}
    missing = sorted(required - serp.keys())
    if missing:
        raise ValueError(f"SERP provider response missing fields: {', '.join(missing)}")
    if serp.get("keyword") != keyword or serp.get("language") != language or serp.get("country") != country:
        raise ValueError("SERP provider response metadata must match the requested query")
    if not isinstance(serp.get("results"), list):
        raise ValueError("SERP provider results must be an array")

    competitor_analysis = analyze_competitors(serp)
    return {
        "analysis_id": _analysis_id(strategy_lineage, keyword, language, country, serp),
        **strategy_lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "serp_analysis_ready",
        "keyword": keyword,
        "language": language,
        "country": country,
        "serp": serp,
        "competitor_analysis": competitor_analysis,
        "audit": {
            "method": "content_strategy_to_realtime_serp_analysis",
            "version": METHOD_VERSION,
            "validation_status": "validated",
            "provider": provider.__class__.__name__,
        },
    }
