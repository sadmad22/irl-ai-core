from collections import Counter, defaultdict
import re
from urllib.parse import urlparse


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


def _classify_result(result: dict, keyword: str) -> tuple[str, float, list[str]]:
    title = result.get("title", "") or ""
    snippet = result.get("snippet", "") or ""
    url = result.get("url", "") or ""
    text = f"{title} {snippet} {url}".lower()
    tokens = _tokens(text)
    query_tokens = _tokens(keyword)

    scores = Counter()
    reasons = defaultdict(list)

    for intent, signals in SIGNALS.items():
        for signal in signals:
            if " " in signal:
                matched = signal in text
            else:
                matched = signal in tokens

            if matched:
                weight = 2 if signal in title.lower() else 1
                scores[intent] += weight
                reasons[intent].append(signal)

    domain = result.get("domain") or urlparse(url).netloc
    title_tokens = _tokens(title)

    if query_tokens and query_tokens.issubset(title_tokens):
        scores["Informational"] += 1
        reasons["Informational"].append("query-aligned-title")

    if domain and any(token in domain.lower() for token in query_tokens if len(token) > 3):
        scores["Navigational"] += 2
        reasons["Navigational"].append("query-aligned-domain")

    if not scores:
        scores["Informational"] = 1
        reasons["Informational"].append("default")

    ordered = scores.most_common()
    intent = ordered[0][0]
    total = sum(scores.values())
    confidence = scores[intent] / total if total else 0.0

    return intent, round(confidence, 4), reasons[intent][:5]


def analyze_serp_intent(serp_data: dict) -> dict:
    """Infer search intent from normalized SERP results."""

    keyword = serp_data.get("keyword", "")
    analyzed_results = []
    weighted_scores = Counter()
    counts = Counter()

    for result in serp_data.get("results", []):
        intent, confidence, reasons = _classify_result(result, keyword)
        position = result.get("position")
        position_weight = 1.0 / position if isinstance(position, int) and position > 0 else 1.0

        weighted_scores[intent] += position_weight
        counts[intent] += 1

        analyzed_results.append(
            {
                "position": position,
                "domain": result.get("domain") or urlparse(result.get("url", "")).netloc,
                "title": result.get("title"),
                "url": result.get("url", ""),
                "intent": intent,
                "confidence": confidence,
                "reasons": reasons,
            }
        )

    if not analyzed_results:
        return {
            "keyword": keyword,
            "country": serp_data.get("country", ""),
            "language": serp_data.get("language", ""),
            "dominant_intent": None,
            "dominant_confidence": 0.0,
            "intent_distribution": {},
            "intent_counts": {},
            "mixed_intent": False,
            "results": [],
        }

    ranked = weighted_scores.most_common()
    dominant_intent, dominant_weight = ranked[0]
    total_weight = sum(weighted_scores.values())
    dominant_confidence = dominant_weight / total_weight if total_weight else 0.0

    intent_distribution = {
        intent: round(weight / total_weight, 4)
        for intent, weight in weighted_scores.items()
    }

    mixed_intent = len(counts) > 1 and dominant_confidence < 0.65

    return {
        "keyword": keyword,
        "country": serp_data.get("country", ""),
        "language": serp_data.get("language", ""),
        "dominant_intent": dominant_intent,
        "dominant_confidence": round(dominant_confidence, 4),
        "intent_distribution": intent_distribution,
        "intent_counts": dict(counts),
        "mixed_intent": mixed_intent,
        "results": analyzed_results,
    }
