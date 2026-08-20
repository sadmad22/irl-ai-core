from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .agent import run as run_research_agent
from .article_draft_agent import run as run_article_draft_agent
from .seo_strategy_agent import run_seo_strategy_agent
from .seo_validation_agent import run_seo_validation_agent
from .editorial_review import build_editorial_review
from .publication_agent import run_publication_agent
from .publisher_agent import run_publisher_agent
from .wordpress_draft_delivery_agent import run_wordpress_draft_delivery_agent
from .wordpress_draft_delivery_client import WordPressConnection, deliver_wordpress_draft


def _save_if_changed(project: str, filename: str, data: dict[str, Any]) -> None:
    path = Path("research") / project / filename
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if current != data:
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


def _load(project: str, filename: str) -> dict[str, Any]:
    return json.loads((Path("research") / project / filename).read_text(encoding="utf-8"))


def build_content_research_to_wordpress_draft(
    *,
    research_report: dict[str, Any],
    content_brief: dict[str, Any],
    article_draft: dict[str, Any],
) -> dict[str, Any]:
    """Connect existing content artifacts through the publication gates to Draft Delivery.

    This function performs no filesystem or network I/O. It composes existing
    engines and preserves their lineage; the final WordPress artifact is always
    draft-only.
    """
    seo_strategy = run_seo_strategy_agent(
        content_brief=content_brief,
        research_report=research_report,
    )
    seo_validation = run_seo_validation_agent(
        article_draft=article_draft,
        seo_strategy=seo_strategy,
    )
    editorial_review = build_editorial_review(article_draft=article_draft)
    publication = run_publication_agent(
        article_draft=article_draft,
        seo_validation=seo_validation,
        editorial_review=editorial_review,
    )

    result: dict[str, Any] = {
        "research_report": research_report,
        "content_brief": content_brief,
        "article_draft": article_draft,
        "seo_strategy": seo_strategy,
        "seo_validation": seo_validation,
        "editorial_review": editorial_review,
        "publication": publication,
    }

    if publication.get("gate_status") != "allowed":
        return result

    publisher = run_publisher_agent(
        publication=publication,
        article_draft=article_draft,
    )
    delivery = run_wordpress_draft_delivery_agent(
        publisher=publisher,
        article_draft=article_draft,
        execution_mode="dry_run",
    )
    result["publisher"] = publisher
    result["wordpress_draft_delivery"] = delivery
    return result


def run_content_research_to_wordpress_draft(
    project_name: str,
    *,
    deliver: bool = False,
    connection: WordPressConnection | None = None,
    transport: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run the established Research/Content pipeline through WordPress Draft.

    By default this prepares the complete delivery contract without network I/O.
    Set ``deliver=True`` only for the already-verified live WordPress Draft path.
    No code path in this pipeline can publish a WordPress post.
    """
    run_research_agent(project_name)
    run_article_draft_agent(project_name)

    artifacts = build_content_research_to_wordpress_draft(
        research_report=_load(project_name, "research-report.json"),
        content_brief=_load(project_name, "content-brief.json"),
        article_draft=_load(project_name, "article-draft.json"),
    )

    artifact_files = {
        "seo_strategy": "seo-strategy.json",
        "seo_validation": "seo-validation.json",
        "editorial_review": "editorial-review.json",
        "publication": "publication.json",
        "publisher": "publisher.json",
        "wordpress_draft_delivery": "wordpress-draft-delivery.json",
    }
    for key, filename in artifact_files.items():
        if key in artifacts:
            _save_if_changed(project_name, filename, artifacts[key])

    publication = artifacts["publication"]
    metadata_path = Path("research") / project_name / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["project_name"] = project_name

    if publication.get("gate_status") != "allowed":
        metadata["status"] = "publication_blocked"
        metadata_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")
        return artifacts

    metadata["status"] = "wordpress_draft_ready"

    if deliver:
        delivery_result = deliver_wordpress_draft(
            delivery=artifacts["wordpress_draft_delivery"],
            connection=connection,
            transport=transport,
        )
        artifacts["wordpress_draft_delivery_result"] = delivery_result
        _save_if_changed(project_name, "wordpress-draft-delivery-result.json", delivery_result)
        metadata["status"] = "wordpress_draft_delivered"

    metadata_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")
    return artifacts
