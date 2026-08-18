from __future__ import annotations
from typing import Any
from .publication import build_publication_gate

def run_publication_agent(*, article_draft: dict[str,Any], seo_validation: dict[str,Any], editorial_review: dict[str,Any]) -> dict[str,Any]:
    """Evaluate publication eligibility only; never publishes or mutates inputs."""
    return build_publication_gate(article_draft=article_draft, seo_validation=seo_validation, editorial_review=editorial_review)
