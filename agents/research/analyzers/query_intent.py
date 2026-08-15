from collections import Counter
import re


INTENTS = (
    "Informational",
    "Commercial",
    "Transactional",
    "Navigational",
)


SIGNALS = {
    "Informational": (
        "what",
        "how",
        "why",
        "guide",
        "explained",
        "definition",
        "meaning",
        "learn",
        "information",
        "faq",
        "tips",
        "requirements",
        "eligibility",
        "cost",
        "coverage",
    ),
    "Commercial": (
        "best",
        "top",
        "review",
        "reviews",
        "compare",
        "comparison",
        "vs",
        "versus",
        "providers",
        "plans",
        "pricing",
        "options",
        "alternatives",
        "worth",
    ),
    "Transactional": (
        "buy",
        "purchase",
        "quote",
        "get a quote",
        "apply",
        "enroll",
        "signup",
        "sign up",
        "subscribe",
        "order",
        "book",
    ),
}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def classify_query_intent(keyword: str) -> dict:
    """Classify intent from the query itself, without using SERP evidence."""

    query = keyword.strip()
    text = query.lower()
    tokens = _tokens(query)
    scores = Counter()
    reasons = {}

    for intent, signals in SIGNALS.items():
        matched = []
        for signal in signals:
            if " " in signal:
                is_match = signal in text
            else:
                is_match = signal in tokens
            if is_match:
                scores[intent] += 2 if signal in text.split() else 1
                matched.append(signal)
        if matched:
            reasons[intent] = matched

    # A named brand/entity query is navigational only when the query has
    # explicit navigational language. Generic product/category queries are not.
    if not scores:
        scores["Informational"] = 1
        reasons["Informational"] = ["no-explicit-intent-signal"]

    ranked = scores.most_common()
    primary_intent, primary_score = ranked[0]
    total_score = sum(scores.values())
    confidence = primary_score / total_score if total_score else 0.0

    secondary_intent = ranked[1][0] if len(ranked) > 1 else None

    return {
        "keyword": query,
        "primary_intent": primary_intent,
        "secondary_intent": secondary_intent,
        "confidence": round(confidence, 4),
        "scores": dict(scores),
        "signals": reasons,
    }
