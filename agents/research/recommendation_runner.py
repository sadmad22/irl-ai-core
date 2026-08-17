from __future__ import annotations

from typing import Any

from .recommendation import build_recommendation


def run_recommendation_from_report(report: dict[str, Any]) -> dict[str, Any]:
    """Generate a recommendation from the canonical pre-decision report."""
    if report.get("lifecycle_stage") != "research_complete":
        raise ValueError("ResearchReport must be at research_complete stage")
    if report.get("recommendation") is not None:
        raise ValueError("ResearchReport already contains a recommendation")
    if report.get("decision") is not None:
        raise ValueError("ResearchReport already contains a decision")

    return build_recommendation(report)
