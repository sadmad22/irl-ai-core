from __future__ import annotations
from typing import Any
from .wordpress_draft_delivery import build_wordpress_draft_delivery

def run_wordpress_draft_delivery_agent(*, publisher: dict[str, Any], article_draft: dict[str, Any], execution_mode: str = "dry_run") -> dict[str, Any]:
    """Prepare immutable WordPress Draft delivery; never publishes externally."""
    return build_wordpress_draft_delivery(publisher=publisher, article_draft=article_draft, execution_mode=execution_mode)
