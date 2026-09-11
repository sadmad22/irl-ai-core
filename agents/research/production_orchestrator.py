from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from shared.utils.article_production_contract import build_article_production

from .content_research_pipeline import run_content_research_to_wordpress_draft

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

STAGES = (
    "research", "intelligence", "configuration", "structure", "draft",
    "editorial_cleanup", "media", "linking", "optimization", "qa", "article_package",
)
StageRunner = Callable[[str, dict[str, Any]], dict[str, Any]]


def _orchestration_id(project_name: str, completed_stages: list[str], lineage: dict[str, str]) -> str:
    raw = json.dumps({"project_name": project_name, "completed_stages": completed_stages, "lineage": lineage, "schema_version": SCHEMA_VERSION}, sort_keys=True, ensure_ascii=False)
    return f"orchestration_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _lineage_from_result(result: dict[str, Any]) -> dict[str, str]:
    article = result.get("article_draft")
    quality = result.get("article_draft_quality")
    if not isinstance(article, dict) or not isinstance(quality, dict):
        return {}
    keys = ("report_id", "decision_id", "strategy_id", "brief_id")
    lineage = {key: str(article[key]) for key in keys if str(article.get(key, "")).strip()}
    if str(article.get("draft_id", "")).strip():
        lineage["draft_id"] = str(article["draft_id"])
    if str(quality.get("quality_id", "")).strip():
        lineage["quality_id"] = str(quality["quality_id"])
    return lineage


def _completed_stages(result: dict[str, Any]) -> list[str]:
    completed: list[str] = []
    if isinstance(result.get("research_report"), dict): completed.append("research")
    if isinstance(result.get("content_brief"), dict): completed.extend(["intelligence", "configuration", "structure"])
    if isinstance(result.get("article_draft"), dict): completed.append("draft")
    if isinstance(result.get("editorial_review"), dict): completed.extend(["editorial_cleanup", "media", "linking"])
    if isinstance(result.get("seo_validation"), dict): completed.append("optimization")
    if isinstance(result.get("article_draft_quality"), dict) and isinstance(result.get("claim_audit"), dict):
        if result.get("publication", {}).get("gate_status") == "allowed": completed.append("qa")
    return list(dict.fromkeys(completed))


def _error_for_result(result: dict[str, Any]) -> dict[str, str] | None:
    quality = result.get("article_draft_quality")
    if isinstance(quality, dict) and quality.get("outcome") != "passed":
        return {"stage": "qa", "type": "QualityGateBlocked", "message": "Article Draft Quality Gate did not pass."}
    claims = result.get("claim_audit")
    if isinstance(claims, dict) and claims.get("outcome") != "passed":
        return {"stage": "qa", "type": "ClaimAuditBlocked", "message": "Claim Audit did not pass."}
    publication = result.get("publication")
    if isinstance(publication, dict) and publication.get("gate_status") != "allowed":
        return {"stage": "qa", "type": "PublicationGateBlocked", "message": "Publication Gate did not allow the production output."}
    return None


def build_production_orchestration(*, project_name: str, result: dict[str, Any]) -> dict[str, Any]:
    completed = _completed_stages(result)
    lineage = _lineage_from_result(result)
    error = _error_for_result(result)
    package = None
    article = result.get("article_draft")
    quality = result.get("article_draft_quality")
    if error is None and isinstance(article, dict) and isinstance(quality, dict):
        package = build_article_production(article=article, quality=quality)
        completed.append("article_package")
    completed = list(dict.fromkeys(completed))
    remaining = [stage for stage in STAGES if stage not in completed]
    lifecycle = "failed" if error else "completed" if not remaining else "running"
    current = None if lifecycle == "completed" else (error["stage"] if error else remaining[0])
    return {
        "orchestration_id": _orchestration_id(project_name, completed, lineage),
        "project_name": project_name, "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": lifecycle, "current_stage": current,
        "completed_stages": completed, "remaining_stages": remaining,
        "lineage": lineage, "article_package": package, "error": error,
        "audit": {"method": "irl_production_orchestrator", "version": METHOD_VERSION, "validation_status": "validated"},
    }


def run_production_orchestrator(
    project_name: str,
    *,
    llm_provider: Any,
    deliver: bool = False,
    connection: Any = None,
    transport: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Coordinate the Core pipeline; article writing requires an injected provider."""
    result = run_content_research_to_wordpress_draft(project_name, llm_provider=llm_provider, deliver=deliver, connection=connection, transport=transport)
    return build_production_orchestration(project_name=project_name, result=result)


def execute_stage_plan(*, project_name: str, stage_runner: StageRunner, start_stage: str = "research", initial_outputs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute explicit stage boundaries with fail-stop and controlled resume semantics."""
    if start_stage not in STAGES: raise ValueError(f"Unknown production stage: {start_stage}")
    context: dict[str, Any] = dict(initial_outputs or {})
    completed = [stage for stage in STAGES if stage in context.get("completed_stages", [])]
    start_index = STAGES.index(start_stage)
    required_prefix = list(STAGES[:start_index])
    if required_prefix and not all(stage in completed for stage in required_prefix): raise ValueError("Resume requires all earlier stage checkpoints to be supplied")
    for stage in STAGES[start_index:]:
        try:
            output = stage_runner(stage, dict(context))
            if not isinstance(output, dict): raise TypeError("Stage runner must return a dictionary")
            context.update(output); completed.append(stage)
        except Exception as exc:
            lineage = _lineage_from_result(context)
            remaining = [item for item in STAGES if item not in completed]
            return {"orchestration_id": _orchestration_id(project_name, completed, lineage), "project_name": project_name, "schema_version": SCHEMA_VERSION, "lifecycle_stage": "failed", "current_stage": stage, "completed_stages": list(dict.fromkeys(completed)), "remaining_stages": remaining, "lineage": lineage, "article_package": context.get("article_package"), "error": {"stage": stage, "type": type(exc).__name__, "message": str(exc)}, "audit": {"method": "irl_production_orchestrator", "version": METHOD_VERSION, "validation_status": "validated"}}
    lineage = _lineage_from_result(context)
    return {"orchestration_id": _orchestration_id(project_name, list(dict.fromkeys(completed)), lineage), "project_name": project_name, "schema_version": SCHEMA_VERSION, "lifecycle_stage": "completed", "current_stage": None, "completed_stages": list(dict.fromkeys(completed)), "remaining_stages": [], "lineage": lineage, "article_package": context.get("article_package"), "error": None, "audit": {"method": "irl_production_orchestrator", "version": METHOD_VERSION, "validation_status": "validated"}}
