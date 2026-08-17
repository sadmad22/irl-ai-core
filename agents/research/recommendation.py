from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _score(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        if 0 <= float(value) <= 1:
            return _clamp(float(value))
        if 0 <= float(value) <= 100:
            return _clamp(float(value) / 100.0)
    if isinstance(value, str):
        mapping = {"high": 1.0, "medium": 0.6, "low": 0.25, "strong": 1.0, "moderate": 0.6, "weak": 0.25}
        return mapping.get(value.strip().lower(), 0.5)
    return 0.5


def _evidence_refs(report: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for values in report.get("evidence_refs", {}).values():
        if isinstance(values, list):
            refs.extend(str(value) for value in values if value)
    return list(dict.fromkeys(refs))


def _intent_fit(report: dict[str, Any]) -> float:
    intent = report.get("search_intent") or {}
    primary = str(intent.get("primary_intent", "")).lower()
    confidence = _score(intent.get("confidence", 0.5))
    if primary == "navigational":
        return round(0.25 * confidence, 4)
    if primary in {"commercial", "transactional", "informational"}:
        return round(0.75 + (0.25 * confidence), 4)
    return 0.5


def _serp_opportunity(report: dict[str, Any]) -> float:
    serp = report.get("serp_analysis") or {}
    results = serp.get("results") if isinstance(serp, dict) else None
    competitors = report.get("competitor_analysis") or {}
    domain_counts = competitors.get("domain_counts") if isinstance(competitors, dict) else None
    if not isinstance(results, list) or not results:
        return 0.5
    total = len(results)
    concentration = 0.0
    if isinstance(domain_counts, dict) and domain_counts:
        concentration = max(domain_counts.values()) / total
    return round(1.0 - concentration, 4)


def _business_value(report: dict[str, Any]) -> float:
    business = report.get("business_analysis") or {}
    if not business:
        return 0.5
    values = [_score(business.get(key)) for key in ("affiliate_potential", "adsense_potential", "conversion_potential", "commercial_value") if key in business]
    return round(sum(values) / len(values), 4) if values else 0.5


def _authority_fit(report: dict[str, Any]) -> float:
    authority = report.get("topical_authority") or {}
    if not authority:
        return 0.5
    values = [_score(authority.get(key)) for key in ("authority_score", "topic_fit") if key in authority]
    return round(sum(values) / len(values), 4) if values else 0.5


def _research_completeness(report: dict[str, Any]) -> float:
    refs = report.get("evidence_refs") or {}
    domains = ("intent", "entity", "question", "business", "authority")
    populated = sum(1 for domain in domains if isinstance(refs.get(domain), list) and refs.get(domain))
    return round(populated / len(domains), 4)


def _content_type(report: dict[str, Any]) -> str | None:
    primary = str((report.get("search_intent") or {}).get("primary_intent", "")).lower()
    return {
        "informational": "guide",
        "commercial": "comparison",
        "transactional": "buyer_guide",
    }.get(primary)


def _recommendation(score: float, completeness: float, intent_fit: float) -> str:
    if intent_fit <= 0.3:
        return "reject"
    if completeness < 0.8:
        return "defer"
    if score >= 70:
        return "pursue"
    if score >= 50:
        return "defer"
    return "reject"


def _priority(score: float, recommendation: str) -> str:
    if recommendation == "reject":
        return "low"
    if score >= 75:
        return "high"
    if score >= 55:
        return "medium"
    return "low"


def _recommendation_id(report_id: str, refs: list[str], criteria: dict[str, float]) -> str:
    payload = json.dumps({"report_id": report_id, "evidence_refs": refs, "criteria": criteria}, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"rec_{digest}"


def build_recommendation(report: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic recommendation from one canonical ResearchReport.

    This engine recommends an action but never creates or mutates a Decision.
    Every recommendation carries the report's evidence references as explicit
    lineage so the recommendation remains auditable back to upstream evidence.
    """
    report_id = str(report.get("report_id", "")).strip()
    if not report_id:
        raise ValueError("ResearchReport.report_id is required")
    if report.get("lifecycle_stage") != "research_complete":
        raise ValueError("Recommendation requires a research_complete ResearchReport")

    refs = _evidence_refs(report)
    if not refs:
        raise ValueError("ResearchReport must contain evidence_refs before recommendation")

    criteria = {
        "intent_fit": _intent_fit(report),
        "serp_opportunity": _serp_opportunity(report),
        "business_value": _business_value(report),
        "authority_fit": _authority_fit(report),
        "research_completeness": _research_completeness(report),
    }
    weights = {
        "intent_fit": 0.25,
        "serp_opportunity": 0.25,
        "business_value": 0.20,
        "authority_fit": 0.20,
        "research_completeness": 0.10,
    }
    score = round(sum(criteria[key] * weights[key] for key in weights) * 100, 2)
    recommendation = _recommendation(score, criteria["research_completeness"], criteria["intent_fit"])
    priority = _priority(score, recommendation)

    rationale = [
        f"Intent fit scored {criteria['intent_fit']:.2f}.",
        f"SERP opportunity scored {criteria['serp_opportunity']:.2f}.",
        f"Business value scored {criteria['business_value']:.2f}.",
        f"Authority fit scored {criteria['authority_fit']:.2f}.",
        f"Research completeness scored {criteria['research_completeness']:.2f}.",
    ]
    if recommendation == "defer":
        rationale.append("Recommendation is deferred until the required research evidence is sufficiently complete.")
    elif recommendation == "reject":
        rationale.append("Current evidence does not support pursuing this opportunity.")
    else:
        rationale.append("Current evidence supports pursuing the opportunity.")

    return {
        "recommendation_id": _recommendation_id(report_id, refs, criteria),
        "report_id": report_id,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "recommendation_ready",
        "recommendation": recommendation,
        "priority": priority,
        "content_type": _content_type(report),
        "score": score,
        "criteria": criteria,
        "rationale": rationale,
        "evidence_refs": refs,
        "audit": {
            "method": "weighted_research_opportunity_score",
            "version": METHOD_VERSION,
            "validation_status": "pending",
        },
    }
