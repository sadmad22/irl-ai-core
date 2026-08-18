from __future__ import annotations

from typing import Any

from .content_brief import build_content_brief


def run_content_brief_from_artifacts(
    *, research_report: dict[str, Any], decision: dict[str, Any], content_strategy: dict[str, Any]
) -> dict[str, Any]:
    """Build a Content Brief from the approved downstream artifacts."""
    return build_content_brief(
        research_report=research_report,
        decision=decision,
        content_strategy=content_strategy,
    )
