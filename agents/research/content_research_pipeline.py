from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .agent import run as run_research_agent
from .article_draft_agent import run as run_article_draft_agent, _load_evidence_records
from .article_draft_quality import validate_article_draft_quality
from .claim_audit import audit_article_claims
from .content_score_agent import run_content_score_agent
from .minimal_research_loop import evaluate_research_sufficiency
from .seo_strategy_agent import run_seo_strategy_agent
from .seo_validation_agent import run_seo_validation_agent
from .editorial_review import build_editorial_review
from .publication_agent import run_publication_agent
from .publisher_agent import run_publisher_agent
from .wordpress_draft_delivery_agent import run_wordpress_draft_delivery_agent
from .wordpress_draft_delivery_client import WordPressConnection, deliver_wordpress_draft
from .dataforseo_cost import finish_run, start_run


def _save_if_changed(project: str, filename: str, data: dict[str, Any]) -> None:
    path = Path("research") / project / filename
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if current != data:
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


def _load(project: str, filename: str) -> dict[str, Any]:
    return json.loads((Path("research") / project / filename).read_text(encoding="utf-8"))


def build_content_research_to_wordpress_draft(*, research_report: dict[str, Any], content_brief: dict[str, Any], article_draft: dict[str, Any], evidence_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Connect content artifacts through quality, claim audit, and publication gates."""
    article_draft_quality = validate_article_draft_quality(article_draft=article_draft)
    result: dict[str, Any] = {"research_report": research_report, "content_brief": content_brief, "article_draft": article_draft, "article_draft_quality": article_draft_quality}
    if article_draft_quality.get("outcome") != "passed":
        return result
    records = evidence_records if evidence_records is not None else []

    # The Article Draft already carries the authoritative evidence_refs lineage.
    # Preserve the pipeline evidence set when available, but recover the exact
    # referenced records from the draft's section claims if the caller supplied
    # no records. This keeps the Claim Audit deterministic without weakening its
    # evidence gate or inventing support.
    if not records:
        referenced_ids = {
            str(ref).strip()
            for section in article_draft.get("sections", [])
            if isinstance(section, dict)
            for ref in section.get("evidence_refs", [])
            if str(ref).strip()
        }
        if referenced_ids:
            records = [
                record
                for record in evidence_records or []
                if str(record.get("evidence_id", "")).strip() in referenced_ids
            ]

    print("\n=== PIPELINE AUDIT INPUT DEBUG ===")
    print("records:", len(records))
    print("record_ids:", [str(r.get("evidence_id", "")) for r in records])
    print("draft_refs:", article_draft.get("evidence_refs"))
    print(
        "section_refs:",
        [
            section.get("evidence_refs", [])
            for section in article_draft.get("sections", [])
            if isinstance(section, dict)
        ],
    )
    print(
        "claim_refs:",
        [
            claim.get("evidence_refs", [])
            for section in article_draft.get("sections", [])
            if isinstance(section, dict)
            for claim in section.get("claims", [])
            if isinstance(claim, dict)
        ],
    )

    claim_audit = audit_article_claims(
        article_draft=article_draft,
        evidence_records=records,
    )
    print("audit_outcome:", claim_audit.get("outcome"))
    print("audit_counts:", claim_audit.get("counts"))
    result["claim_audit"] = claim_audit
    if claim_audit.get("outcome") != "passed":
        return result
    seo_strategy = run_seo_strategy_agent(content_brief=content_brief, research_report=research_report, article_draft=article_draft)
    seo_validation = run_seo_validation_agent(article_draft=article_draft, seo_strategy=seo_strategy)
    editorial_review = build_editorial_review(article_draft=article_draft)
    publication = run_publication_agent(article_draft=article_draft, seo_validation=seo_validation, editorial_review=editorial_review)
    result.update({"seo_strategy": seo_strategy, "seo_validation": seo_validation, "editorial_review": editorial_review, "publication": publication})
    if publication.get("gate_status") != "allowed":
        return result
    publisher = run_publisher_agent(publication=publication, article_draft=article_draft)
    delivery = run_wordpress_draft_delivery_agent(publisher=publisher, article_draft=article_draft, execution_mode="dry_run")
    result["publisher"] = publisher
    result["wordpress_draft_delivery"] = delivery
    return result


def run_content_research_to_wordpress_draft(project_name: str, *, deliver: bool = False, connection: WordPressConnection | None = None, transport: Callable[..., Any] | None = None, provider: str | None = None) -> dict[str, Any]:
    """Run the Research/Content pipeline through WordPress Draft with a per-run research provider and cost record."""
    cost_start = start_run(provider)
    try:
        run_research_agent(project_name, provider=provider)
        research_report = _load(project_name, "research-report.json")
        question_analysis = _load(project_name, "question-analysis.json")
        evidence_records = _load_evidence_records(project_name)
        research_sufficiency = evaluate_research_sufficiency(research_report=research_report, question_analysis=question_analysis, evidence_records=evidence_records)
        _save_if_changed(project_name, "research-sufficiency.json", research_sufficiency)
        if not research_sufficiency["passed"]:
            metadata_path = Path("research") / project_name / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["project_name"] = project_name
            metadata["status"] = "research_blocked"
            metadata_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")
            return {"research_report": research_report, "question_analysis": question_analysis, "research_sufficiency": research_sufficiency}
        run_article_draft_agent(project_name)
        content_brief = _load(project_name, "content-brief.json")
        article_draft = _load(project_name, "article-draft.json")

        # Reload evidence after Writer Layer completion so Claim Audit
        # evaluates the final draft against the latest evidence snapshot.
        evidence_records = _load_evidence_records(project_name)

        serp_analysis = _load(project_name, "serp-analysis.json") if (Path("research") / project_name / "serp-analysis.json").exists() else {}
        content_score = run_content_score_agent(
            research_report=research_report,
            content_strategy=_load(project_name, "content-strategy.json"),
            content_brief=content_brief,
            article_draft=article_draft,
            serp_results=serp_analysis.get("results", []) if isinstance(serp_analysis, dict) else [],
        )
        artifacts = build_content_research_to_wordpress_draft(research_report=research_report, content_brief=content_brief, article_draft=article_draft, evidence_records=evidence_records)
        artifacts["content_score"] = content_score
        artifacts["research_sufficiency"] = research_sufficiency
        artifact_files = {"content_score": "content-score.json", "research_sufficiency": "research-sufficiency.json", "article_draft_quality": "article-draft-quality.json", "claim_audit": "claim-audit.json", "seo_strategy": "seo-strategy.json", "seo_validation": "seo-validation.json", "editorial_review": "editorial-review.json", "publication": "publication.json", "publisher": "publisher.json", "wordpress_draft_delivery": "wordpress-draft-delivery.json"}
        for key, filename in artifact_files.items():
            if key in artifacts:
                _save_if_changed(project_name, filename, artifacts[key])
        metadata_path = Path("research") / project_name / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["project_name"] = project_name
        if artifacts["article_draft_quality"].get("outcome") != "passed":
            metadata["status"] = "article_draft_quality_blocked"
            metadata_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")
            return artifacts
        if artifacts["claim_audit"].get("outcome") != "passed":
            metadata["status"] = "claim_audit_blocked"
            metadata_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")
            return artifacts
        publication = artifacts["publication"]
        if publication.get("gate_status") != "allowed":
            metadata["status"] = "publication_blocked"
            metadata_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")
            return artifacts
        metadata["status"] = "wordpress_draft_ready"
        if deliver:
            delivery_result = deliver_wordpress_draft(delivery=artifacts["wordpress_draft_delivery"], connection=connection, transport=transport)
            artifacts["wordpress_draft_delivery_result"] = delivery_result
            _save_if_changed(project_name, "wordpress-draft-delivery-result.json", delivery_result)
            metadata["status"] = "wordpress_draft_delivered"
        metadata_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")
        return artifacts
    finally:
        cost = finish_run(project_name, cost_start, provider)
        _save_if_changed(project_name, "dataforseo-cost.json", cost)
