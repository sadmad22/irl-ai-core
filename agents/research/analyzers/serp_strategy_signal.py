INTENTS = {
    "Informational",
    "Commercial",
    "Transactional",
    "Navigational",
}


def analyze_serp_strategy_signal(
    intent_alignment: dict,
) -> dict:
    """Convert intent alignment evidence into a conservative strategy signal."""

    keyword = intent_alignment.get("keyword", "")
    primary_intent = intent_alignment.get("query_primary_intent")
    dominant_serp_intent = intent_alignment.get("serp_dominant_intent")
    alignment = intent_alignment.get("alignment")
    confidence = float(intent_alignment.get("confidence", 0.0) or 0.0)

    if (
        primary_intent not in INTENTS
        or dominant_serp_intent not in INTENTS
        or alignment == "indeterminate"
    ):
        strategy_signal = "indeterminate"
    elif alignment == "mixed":
        strategy_signal = "mixed"
    elif alignment == "misaligned":
        strategy_signal = "mixed"
    elif alignment == "aligned":
        strategy_signal = primary_intent.lower()
    else:
        strategy_signal = "indeterminate"

    return {
        "keyword": keyword,
        "primary_intent": primary_intent,
        "dominant_serp_intent": dominant_serp_intent,
        "alignment": alignment,
        "strategy_signal": strategy_signal,
        "confidence": round(confidence, 4),
    }