from __future__ import annotations

from typing import Any

METHOD_VERSION = "business-v1"


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _number(data: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def analyze_business(keyword_data: dict[str, Any], search_intent: dict[str, Any], search_metrics: dict[str, Any]) -> dict[str, Any]:
    """Estimate minimum business signals from observable query/metric inputs.

    This is an opportunity signal, not revenue forecasting.
    """
    intent = str(search_intent.get("primary_intent", "")).lower()
    cpc = _number(search_metrics, "cpc", "cost_per_click")
    volume = _number(search_metrics, "search_volume", "volume")
    competition = _number(search_metrics, "competition", "keyword_difficulty")

    commercial = 1.0 if intent == "commercial" else 0.75 if intent == "transactional" else 0.35 if intent == "mixed" else 0.15
    cpc_signal = _clamp((cpc or 0.0) / 10.0)
    volume_signal = _clamp((volume or 0.0) / 10000.0)
    competition_signal = _clamp(1.0 - (competition or 0.0))
    commercial_value = _clamp(0.5 * commercial + 0.25 * cpc_signal + 0.25 * volume_signal)

    if commercial_value >= 0.7:
        level = "high"
    elif commercial_value >= 0.4:
        level = "medium"
    else:
        level = "low"

    return {
        "affiliate_potential": level,
        "adsense_potential": "high" if volume_signal >= 0.5 else "medium" if volume_signal >= 0.2 else "low",
        "conversion_potential": "high" if commercial >= 0.75 else "medium" if commercial >= 0.35 else "low",
        "commercial_value": level,
        "commercial_value_score": commercial_value,
        "cpc_signal": cpc_signal,
        "volume_signal": volume_signal,
        "competition_signal": competition_signal,
        "method": METHOD_VERSION,
        "keyword": keyword_data.get("keyword"),
    }
