from __future__ import annotations
from typing import Any
from .wordpress_publishing_adapter import build_wordpress_publishing_request

def run_wordpress_publishing_adapter_agent(*, publisher: dict[str, Any], article_draft: dict[str, Any], execution_mode: str = "dry_run") -> dict[str, Any]:
    """Prepare a WordPress REST request; never performs network I/O."""
    return build_wordpress_publishing_request(
        publisher=publisher,
        article_draft=article_draft,
        execution_mode=execution_mode,
    )
