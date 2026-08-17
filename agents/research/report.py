from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0"


def _refs(items: list[dict[str, Any]] | None) -> list[str]:
    if not items:
        return []
    return list(dict.fromkeys(item["evidence_id"] for item in items))


def _stable_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Keep report metadata stable across lifecycle status transitions."""
    return {key: value for key, value in metadata.items() if key != "status"}


def build_research_report(
    *,
    report_id: str,
    metadata: dict[str, Any],
    keyword: dict[str, Any],
    search_intent: dict[str, Any] | None,
    search_metrics: dict[str, Any],
    serp_analysis: dict[str, Any],
    competitor_analysis: dict[str, Any],
    entity_analysis: dict[str, Any] | None = None,
    question_analysis: dict[str, Any] | None = None,
    topical_authority: dict[str, Any] | None = None,
    business_analysis: dict[str, Any] | None = None,
    intent_evidence: list[dict[str, Any]] | None = None,
    entity_evidence: list[dict[str, Any]] | None = None,
    question_evidence: list[dict[str, Any]] | None = None,
    business_evidence: list[dict[str, Any]] | None = None,
    authority_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Assemble the canonical pre-decision research state."""
    if not report_id:
        raise ValueError("report_id is required")
    if not keyword.get("keyword"):
        raise ValueError("keyword.keyword is required")

    return {
        "report_id": report_id,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "research_complete",
        "metadata": _stable_metadata(metadata),
        "keyword": dict(keyword),
        "search_intent": dict(search_intent) if search_intent is not None else None,
        "search_metrics": dict(search_metrics),
        "serp_analysis": dict(serp_analysis),
        "competitor_analysis": dict(competitor_analysis),
        "entity_analysis": dict(entity_analysis or {}),
        "question_analysis": dict(question_analysis or {}),
        "topical_authority": dict(topical_authority or {}),
        "business_analysis": dict(business_analysis or {}),
        "evidence_refs": {
            "intent": _refs(intent_evidence),
            "entity": _refs(entity_evidence),
            "question": _refs(question_evidence),
            "business": _refs(business_evidence),
            "authority": _refs(authority_evidence),
        },
        "recommendation": None,
        "decision": None,
        "audit": {
            "validation_status": "pending",
            "validation_errors": [],
            "notes": ["Pre-decision research state; recommendation and decision are intentionally not generated."],
        },
    }
