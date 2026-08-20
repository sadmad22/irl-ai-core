from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"


def _brief_id(report_id: str, decision_id: str, strategy_id: str, payload: dict[str, Any]) -> str:
    raw = json.dumps(
        {"report_id": report_id, "decision_id": decision_id, "strategy_id": strategy_id, "brief": payload},
        sort_keys=True,
    )
    return f"brief_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _intent(report: dict[str, Any]) -> str:
    return str((report.get("search_intent") or {}).get("primary_intent", "")).strip().lower() or "unknown"


def _objective(strategy: dict[str, Any]) -> str:
    goal = str(strategy.get("business_goal", "")).strip()
    if goal:
        return goal
    return "Produce a useful, evidence-led resource aligned with the approved content strategy."


def _title_direction(keyword: str, content_type: str) -> str:
    templates = {
        "guide": f"Use the primary topic '{keyword}' with a clear, benefit-led guide framing; do not treat this as a final headline.",
        "comparison": f"Frame '{keyword}' around a transparent comparison and the criteria readers need to evaluate options.",
        "buyer_guide": f"Frame '{keyword}' as a practical buyer decision guide focused on coverage, cost, trade-offs, and selection criteria.",
        "article": f"Use '{keyword}' as the central topic with a clear informational framing and reader-first value proposition.",
    }
    return templates[content_type]


def _outline(strategy: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"heading": section, "purpose": f"Address the '{section}' requirement from the approved content strategy without introducing unsupported claims."}
        for section in strategy.get("sections", [])
    ]


def _constraints(strategy: dict[str, Any]) -> list[str]:
    return [
        "Use evidence_refs as the authoritative upstream lineage for factual claims.",
        "Do not invent providers, prices, coverage terms, statistics, or regulatory claims absent supporting evidence.",
        "Do not make the brief itself a final article draft; prose generation belongs to the Writer layer.",
        "Do not change the approved Decision or create a new operational decision.",
    ]


def build_content_brief(*, research_report: dict[str, Any], decision: dict[str, Any], content_strategy: dict[str, Any]) -> dict[str, Any]:
    """Translate Content Strategy into a production specification.

    The brief is downstream of Decision and Strategy. It does not re-score
    evidence, change the decision, or generate article prose.
    """
    report_id = str(research_report.get("report_id", "")).strip()
    decision_id = str(decision.get("decision_id", "")).strip()
    strategy_id = str(content_strategy.get("strategy_id", "")).strip()
    if not report_id or not decision_id or not strategy_id:
        raise ValueError("ResearchReport.report_id, Decision.decision_id, and ContentStrategy.strategy_id are required")
    if research_report.get("lifecycle_stage") != "research_complete":
        raise ValueError("Content Brief requires a research_complete ResearchReport")
    if decision.get("lifecycle_stage") != "decision_ready" or decision.get("outcome") != "approved":
        raise ValueError("Content Brief requires an approved decision_ready Decision")
    if decision.get("report_id") != report_id:
        raise ValueError("Decision.report_id must match ResearchReport.report_id")
    if content_strategy.get("lifecycle_stage") != "content_strategy_ready":
        raise ValueError("Content Brief requires a content_strategy_ready Content Strategy")
    if content_strategy.get("report_id") != report_id:
        raise ValueError("Content Strategy.report_id must match ResearchReport.report_id")
    if content_strategy.get("decision_id") != decision_id:
        raise ValueError("Content Strategy.decision_id must match Decision.decision_id")

    refs = content_strategy.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        raise ValueError("Content Strategy must contain explicit evidence_refs")

    content_type = content_strategy.get("content_type")
    keyword = str(content_strategy.get("primary_keyword", "")).strip()
    if not keyword:
        raise ValueError("Content Strategy.primary_keyword is required")
    if content_type not in {"guide", "comparison", "buyer_guide", "article"}:
        raise ValueError("Content Strategy.content_type is invalid")

    payload = {
        "content_type": content_type,
        "primary_keyword": keyword,
        "search_intent": _intent(research_report),
        "audience": str(content_strategy.get("audience", "")).strip(),
        "objective": _objective(content_strategy),
        "title_direction": _title_direction(keyword, content_type),
        "outline": _outline(content_strategy),
        "required_entities": list(dict.fromkeys(str(v).strip() for v in content_strategy.get("entities", []) if str(v).strip())),
        "required_questions": list(dict.fromkeys(str(v).strip() for v in content_strategy.get("questions", []) if str(v).strip())),
        "evidence_refs": list(dict.fromkeys(str(v) for v in refs if str(v).strip())),
        "editorial_constraints": _constraints(content_strategy),
    }

    return {
        "brief_id": _brief_id(report_id, decision_id, strategy_id, payload),
        "report_id": report_id,
        "decision_id": decision_id,
        "strategy_id": strategy_id,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "content_brief_ready",
        **payload,
        "audit": {
            "method": "content_strategy_to_content_brief",
            "version": METHOD_VERSION,
            "validation_status": "pending",
        },
    }
