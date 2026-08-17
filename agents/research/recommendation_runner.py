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

    evidence_refs = report.get("evidence_refs", {})
    refs = []
    for values in evidence_refs.values():
        refs.extend(values)

    return build_recommendation(
        report_id=report["report_id"],
        research_report=report,
        evidence_refs=list(dict.fromkeys(refs)),
    )
