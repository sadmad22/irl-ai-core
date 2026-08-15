INTENTS = {"Informational", "Commercial", "Transactional", "Navigational"}


def analyze_intent_alignment(query_intent: dict, serp_intent: dict) -> dict:
    """Compare query intent with the dominant SERP intent."""
    keyword = query_intent.get("keyword") or serp_intent.get("keyword", "")
    query_primary = query_intent.get("primary_intent")
    serp_dominant = serp_intent.get("dominant_intent")
    serp_mixed = bool(serp_intent.get("mixed_intent", False))
    serp_confidence = float(serp_intent.get("dominant_confidence", 0.0) or 0.0)
    intent_distribution = serp_intent.get("intent_distribution", {})

    if query_primary not in INTENTS or serp_dominant not in INTENTS:
        return {
            "keyword": keyword,
            "query_primary_intent": query_primary,
            "serp_dominant_intent": serp_dominant,
            "alignment": "indeterminate",
            "confidence": 0.0,
            "serp_mixed": serp_mixed,
            "intent_distribution": intent_distribution,
        }

    if query_primary == serp_dominant and not serp_mixed:
        alignment = "aligned"
    elif query_primary == serp_dominant and serp_mixed:
        alignment = "mixed"
    else:
        alignment = "misaligned"

    return {
        "keyword": keyword,
        "query_primary_intent": query_primary,
        "serp_dominant_intent": serp_dominant,
        "alignment": alignment,
        "confidence": round(serp_confidence, 4),
        "serp_mixed": serp_mixed,
        "intent_distribution": intent_distribution,
    }
