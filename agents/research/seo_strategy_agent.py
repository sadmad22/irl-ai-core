from __future__ import annotations
from typing import Any
from .seo_strategy import build_seo_strategy

def run_seo_strategy_agent(
    *,
    content_brief: dict[str, Any],
    research_report: dict[str, Any],
    article_draft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_seo_strategy(
        content_brief=content_brief,
        research_report=research_report,
        article_draft=article_draft,
    )
