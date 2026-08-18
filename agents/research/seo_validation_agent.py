from __future__ import annotations
from typing import Any
from .seo_validation import validate_seo

def run_seo_validation_agent(*, article_draft: dict[str, Any], seo_strategy: dict[str, Any]) -> dict[str, Any]:
    """Run the SEO validation gate without mutating upstream artifacts."""
    return validate_seo(article_draft=article_draft, seo_strategy=seo_strategy)
