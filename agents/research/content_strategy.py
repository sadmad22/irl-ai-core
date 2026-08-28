from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"


def _strategy_id(report_id: str, decision_id: str, payload: dict[str, Any]) -> str:
    raw = json.dumps({"report_id": report_id, "decision_id": decision_id, "strategy": payload}, sort_keys=True)
    return f"strat_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _keyword(report: dict[str, Any]) -> str:
    value = report.get("keyword")
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        for key in ("text", "keyword", "value"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    raise ValueError("ResearchReport.keyword is required for Content Strategy")


def _intent(report: dict[str, Any]) -> str:
    return str((report.get("search_intent") or {}).get("primary_intent", "")).strip().lower()


def _content_type(report: dict[str, Any], recommendation: dict[str, Any]) -> str:
    value = recommendation.get("content_type")
    if value in {"guide", "comparison", "buyer_guide", "article"}:
        return value
    return {"informational": "guide", "commercial": "comparison", "transactional": "buyer_guide"}.get(_intent(report), "article")


def _audience(report: dict[str, Any]) -> str:
    intent = _intent(report)
    return {
        "informational": "Readers seeking clear, trustworthy insurance information",
        "commercial": "Readers comparing insurance options before choosing a provider",
        "transactional": "Readers with near-term intent to evaluate or purchase insurance",
        "navigational": "Readers seeking a specific insurance brand or destination",
    }.get(intent, "Readers researching an insurance topic")


def _angle(report: dict[str, Any], content_type: str) -> str:
    keyword = _keyword(report)
    if content_type == "comparison":
        return f"Independent, evidence-led comparison of the key options for {keyword}."
    if content_type == "buyer_guide":
        return f"Practical decision guide covering coverage, costs, trade-offs, and selection criteria for {keyword}."
    return f"Independent, evidence-led guide explaining {keyword} and the factors readers need to evaluate."


def _format(content_type: str) -> str:
    return {
        "guide": "structured long-form guide",
        "comparison": "comparison-led long-form article",
        "buyer_guide": "decision-oriented buyer guide",
        "article": "structured informational article",
    }[content_type]


def _sections(content_type: str) -> list[str]:
    base = ["Introduction", "What You Need to Know", "Coverage and Key Factors", "Costs and Pricing Factors", "How to Compare Options", "Frequently Asked Questions", "Sources and Editorial Methodology"]
    if content_type == "comparison":
        return ["Introduction", "Quick Comparison", "What Each Option Covers", "Costs and Value", "Pros and Cons", "How to Choose", "Frequently Asked Questions", "Sources and Editorial Methodology"]
    if content_type == "buyer_guide":
        return ["Introduction", "What Coverage You Need", "Costs and Limits", "Key Selection Criteria", "Common Mistakes", "How to Choose", "Frequently Asked Questions", "Sources and Editorial Methodology"]
    return base


def _entities(report: dict[str, Any]) -> list[str]:
    analysis = report.get("entity_analysis") or {}
    values = analysis.get("entities") if isinstance(analysis, dict) else None
    if not isinstance(values, list):
        return []
    result = []
    for item in values:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            value = item.get("name") or item.get("entity")
            if isinstance(value, str) and value.strip():
                result.append(value.strip())
    return list(dict.fromkeys(result))


def _questions(report: dict[str, Any]) -> list[Any]:
    analysis = report.get("question_analysis") or {}
    values = analysis.get("questions") if isinstance(analysis, dict) else None
    if not isinstance(values, list):
        return []

    result: list[Any] = []
    seen: set[str] = set()

    for value in values:
        if isinstance(value, str):
            if not value.strip():
                continue
            key = json.dumps(value.strip(), ensure_ascii=False, sort_keys=True)
            normalized = value.strip()
        elif isinstance(value, dict):
            key = json.dumps(value, ensure_ascii=False, sort_keys=True)
            normalized = value
        else:
            key = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
            normalized = value

        if key in seen:
            continue

        seen.add(key)
        result.append(normalized)

    return result


def _business_goal(report: dict[str, Any]) -> str:
    business = report.get("business_analysis") or {}
    value = str(business.get("commercial_value", "")).lower()
    if value in {"high", "strong"}:
        return "Build qualified organic traffic and support commercially relevant insurance decisions."
    return "Build qualified organic traffic and provide trustworthy insurance guidance."


def build_content_strategy(*, research_report: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    """Translate an approved operational Decision into a production strategy.

    This engine does not create a new decision, evaluate upstream evidence,
    or write article prose. It defines what should be produced and preserves
    lineage to the decision and its upstream evidence.
    """
    report_id = str(research_report.get("report_id", "")).strip()
    decision_id = str(decision.get("decision_id", "")).strip()
    if not report_id or not decision_id:
        raise ValueError("ResearchReport.report_id and Decision.decision_id are required")
    if research_report.get("lifecycle_stage") != "research_complete":
        raise ValueError("Content Strategy requires a research_complete ResearchReport")
    if decision.get("report_id") != report_id:
        raise ValueError("Decision.report_id must match ResearchReport.report_id")
    if decision.get("lifecycle_stage") != "decision_ready":
        raise ValueError("Content Strategy requires a decision_ready Decision")
    if decision.get("outcome") != "approved":
        raise ValueError("Content Strategy can only be generated from an approved Decision")

    refs = decision.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        raise ValueError("Decision must contain explicit evidence_refs")

    content_type = _content_type(research_report, {"content_type": decision.get("content_type")})
    payload = {
        "content_type": content_type,
        "primary_keyword": _keyword(research_report),
        "audience": _audience(research_report),
        "angle": _angle(research_report, content_type),
        "format": _format(content_type),
        "sections": _sections(content_type),
        "entities": _entities(research_report),
        "questions": _questions(research_report),
        "business_goal": _business_goal(research_report),
        "evidence_refs": list(dict.fromkeys(str(ref) for ref in refs if ref)),
    }
    return {
        "strategy_id": _strategy_id(report_id, decision_id, payload),
        "report_id": report_id,
        "decision_id": decision_id,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "content_strategy_ready",
        **payload,
        "audit": {
            "method": "decision_to_content_strategy",
            "version": METHOD_VERSION,
            "validation_status": "pending",
        },
    }
