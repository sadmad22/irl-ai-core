from __future__ import annotations

from typing import Any

from .content_strategy import build_content_strategy


def run_content_strategy_from_report(
    report: dict[str, Any], decision: dict[str, Any]
) -> dict[str, Any]:
    """Generate Content Strategy from an existing approved Decision."""
    if report.get("lifecycle_stage") != "research_complete":
        raise ValueError("ResearchReport must be at research_complete stage")
    if decision.get("lifecycle_stage") != "decision_ready":
        raise ValueError("Decision must be at decision_ready stage")
    if decision.get("outcome") != "approved":
        raise ValueError("Content Strategy requires an approved Decision")
    if decision.get("report_id") != report.get("report_id"):
        raise ValueError("Decision.report_id must match ResearchReport.report_id")

    return build_content_strategy(research_report=report, decision=decision)
