from __future__ import annotations

from typing import Any

from .decision import build_decision


def run_decision_from_report(
    report: dict[str, Any], recommendation: dict[str, Any]
) -> dict[str, Any]:
    """Create the operational decision from an existing recommendation.

    The runner enforces the lifecycle boundary and delegates the transition to
    the Decision Engine. It never re-scores research evidence.
    """
    if report.get("lifecycle_stage") != "research_complete":
        raise ValueError("ResearchReport must be at research_complete stage")
    if report.get("recommendation") is not None:
        raise ValueError("ResearchReport must not embed a recommendation")
    if report.get("decision") is not None:
        raise ValueError("ResearchReport must not embed a decision")
    if recommendation.get("lifecycle_stage") != "recommendation_ready":
        raise ValueError("Recommendation must be at recommendation_ready stage")
    if recommendation.get("report_id") != report.get("report_id"):
        raise ValueError("Recommendation.report_id must match ResearchReport.report_id")

    return build_decision(research_report=report, recommendation=recommendation)
