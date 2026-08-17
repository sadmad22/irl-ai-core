from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"


def _decision_id(report_id: str, recommendation_id: str, outcome: str) -> str:
    payload = json.dumps(
        {"report_id": report_id, "recommendation_id": recommendation_id, "outcome": outcome},
        sort_keys=True,
    )
    return f"dec_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _outcome(recommendation: str) -> str:
    mapping = {
        "pursue": "approved",
        "reject": "rejected",
        "defer": "deferred",
    }
    try:
        return mapping[recommendation]
    except KeyError as exc:
        raise ValueError("Recommendation must be pursue, defer, or reject") from exc


def build_decision(*, research_report: dict[str, Any], recommendation: dict[str, Any]) -> dict[str, Any]:
    """Convert an existing recommendation into an operational decision.

    This engine never re-evaluates research evidence and never creates a new
    recommendation. Decision is a strict downstream state transition.
    """
    report_id = str(research_report.get("report_id", "")).strip()
    recommendation_id = str(recommendation.get("recommendation_id", "")).strip()
    if not report_id:
        raise ValueError("ResearchReport.report_id is required")
    if research_report.get("lifecycle_stage") != "research_complete":
        raise ValueError("Decision requires a research_complete ResearchReport")
    if not recommendation_id:
        raise ValueError("Recommendation.recommendation_id is required")
    if recommendation.get("report_id") != report_id:
        raise ValueError("Recommendation.report_id must match ResearchReport.report_id")
    if recommendation.get("lifecycle_stage") != "recommendation_ready":
        raise ValueError("Decision requires a recommendation_ready Recommendation")

    refs = recommendation.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        raise ValueError("Recommendation must contain explicit evidence_refs")

    recommendation_ref = recommendation_id
    outcome = _outcome(str(recommendation.get("recommendation", "")).strip().lower())
    rationale = [
        f"Decision follows the existing recommendation: {recommendation['recommendation']}.",
        "Decision does not independently re-score or reinterpret upstream evidence.",
    ]
    if outcome == "approved":
        rationale.append("The recommendation to pursue is accepted as the operational decision.")
    elif outcome == "rejected":
        rationale.append("The recommendation to reject is accepted as the operational decision.")
    else:
        rationale.append("The recommendation to defer is accepted as the operational decision.")

    return {
        "decision_id": _decision_id(report_id, recommendation_id, outcome),
        "report_id": report_id,
        "recommendation_id": recommendation_id,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "decision_ready",
        "outcome": outcome,
        "rationale": rationale,
        "recommendation_ref": recommendation_ref,
        "evidence_refs": list(dict.fromkeys(str(ref) for ref in refs if ref)),
        "audit": {
            "method": "recommendation_to_decision_transition",
            "version": METHOD_VERSION,
            "validation_status": "pending",
        },
    }
