from __future__ import annotations

from collections import Counter
from typing import Any

METHOD_VERSION = "authority-v1"


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def analyze_authority(keyword_data: dict[str, Any], serp_analysis: dict[str, Any], competitor_analysis: dict[str, Any], search_intent: dict[str, Any]) -> dict[str, Any]:
    """Produce minimum SERP-grounded authority and topic-fit signals.

    This does not assert domain-level E-E-A-T. It measures how clearly the
    observed SERP is topically coherent and how concentrated the competitive set is.
    """
    results = serp_analysis.get("results", []) or []
    domains = [str(r.get("domain", "")).lower() for r in results if r.get("domain")]
    counts = Counter(domains)
    n = len(domains)
    concentration = max(counts.values()) / n if n and counts else 0.0
    diversity = _clamp(1.0 - concentration)
    intent_confidence = search_intent.get("confidence", 0.0)
    try:
        intent_confidence = float(intent_confidence)
    except (TypeError, ValueError):
        intent_confidence = 0.0
    topic_fit = _clamp(0.7 * intent_confidence + 0.3 * diversity)
    authority_score = _clamp(0.5 * topic_fit + 0.5 * diversity)
    return {
        "authority_score": authority_score,
        "topic_fit": topic_fit,
        "serp_domain_diversity": diversity,
        "serp_domain_count": len(counts),
        "method": METHOD_VERSION,
        "keyword": keyword_data.get("keyword"),
        "competitor_domains": competitor_analysis.get("domain_counts", counts),
    }
