from __future__ import annotations

from typing import Any

from .content_score import build_content_score


def run_content_score_agent(*, research_report: dict[str, Any], content_strategy: dict[str, Any], content_brief: dict[str, Any], article_draft: dict[str, Any], serp_results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run the deterministic Content Score layer without changing any gate."""
    return build_content_score(
        research_report=research_report,
        content_strategy=content_strategy,
        content_brief=content_brief,
        article_draft=article_draft,
        serp_results=serp_results,
    )
