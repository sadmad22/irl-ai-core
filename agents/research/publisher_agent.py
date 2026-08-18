from __future__ import annotations
from typing import Any
from .publisher import build_publisher

def run_publisher_agent(*, publication: dict[str, Any], article_draft: dict[str, Any]) -> dict[str, Any]:
    """Prepare an allowed publication for execution; does not perform external publishing."""
    return build_publisher(publication=publication, article_draft=article_draft)
