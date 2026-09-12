from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Callable

from .article_package_engine import build_article_package
from .content_research_pipeline import run_content_research_to_wordpress_draft
from .production_assembly_engine import build_production_assembly
from .production_delivery_boundary_engine import build_production_delivery_boundary
from .wordpress_delivery_adapter import deliver_wordpress_delivery_boundary

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
STAGES = (
    "research", "intelligence", "configuration", "structure", "draft", "editorial_cleanup", "media", "linking", "optimization", "qa",
    "production_assembly", "article_package", "production_delivery_boundary", "wordpress_delivery",
)
PRODUCTION_INTENT = {"target": "wordpress", "mode": "wordpress_draft", "publish": False, "human_approval_required": True}
DELIVERY_MODES = ("live", "dry_run")
StageRunner = Callable[[str, dict[str, Any]], dict[str, Any]]


def _orchestration_id(project_name: str, completed_stages: list[str], lineage: dict[str, str]) -> str:
    raw = json.dumps({"project_name": project_name, "completed_stages": completed_stages, "lineage": lineage, "schema_version": SCHEMA_VERSION}, sort_keys=True, ensure_ascii=False)
    return f"orchestration_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _lineage_from_result(result: dict[str, Any]) -> dict[str, str]:
    lineage: dict[str, str] = {}

    def merge(source: dict[str, Any], keys: tuple[str, ...], source_name: str) -> None:
        for key in keys:
            value = str(source.get(key, "")).strip()
            if not value:
                continue
            if key in lineage and lineage[key] != value:
                raise ValueError(f"Conflicting lineage for {key}: {lineage[key]} != {value} ({source_name})")
            lineage[key] = value

    explicit = result.get("lineage")
    if isinstance(explicit, dict):
        merge(explicit, ("report_id", "decision_id", "strategy_id", "brief_id", "draft_id", "quality_id"), "lineage")

    article = result.get("article_draft")
    if isinstance(article, dict):
        merge(article, ("report_id", "decision_id", "strategy_id", "brief_id", "draft_id", "quality_id"), "article_draft")

    quality = result.get("article_draft_quality") or result.get("quality")
    if isinstance(quality, dict):
        merge(quality, ("report_id", "decision_id", "strategy_id", "brief_id", "draft_id", "quality_id"), "quality")

    return lineage


def _canonical_artifacts(result: dict[str, Any]) -> dict[str, Any]:
    linking = result.get("linking")
    if linking is None and ("internal_linking" in result or "external_linking" in result):
        linking = {"internal": copy.deepcopy(result.get("internal_linking")), "external": copy.deepcopy(result.get("external_linking"))}
    supplied_intent = result.get("production_intent")
    if supplied_intent is not None and supplied_intent != PRODUCTION_INTENT:
        raise ValueError("Conflicting production intent: canonical draft-only WordPress intent is required")
    return {
        "article_draft": result.get("article_draft"), "quality": result.get("quality", result.get("article_draft_quality")),
        "claim_audit": result.get("claim_audit"), "editorial_review": result.get("editorial_review"),
        "optimization": result.get("optimization", result.get("seo_validation")), "media": result.get("media", result.get("media_strategy")),
        "linking": linking, "taxonomy": result.get("taxonomy"), "production_intent": copy.deepcopy(PRODUCTION_INTENT), "lineage": _lineage_from_result(result),
    }


def _checkpoint_from_assembly(value: dict[str, Any]) -> dict[str, Any]:
    return {"assembly_id": value["assembly_id"], "lifecycle_stage": value["lifecycle_stage"]}


def _checkpoint_from_package(value: dict[str, Any]) -> dict[str, Any]:
    return {"package_id": value["identity"]["package_id"], "lifecycle_stage": value["identity"]["lifecycle_stage"], "validation_status": value["audit"]["validation_status"]}


def _checkpoint_from_boundary(value: dict[str, Any]) -> dict[str, Any]:
    return {"delivery_id": value["delivery_id"], "lifecycle_stage": value["lifecycle_stage"], "delivery_status": value["delivery_status"]}


def _checkpoint_from_wordpress(value: dict[str, Any], *, live: bool) -> dict[str, Any]:
    checkpoint = {"execution_mode": "live" if live else "dry_run", "delivery_status": "delivered" if live else "ready", "publish": False, "human_approval_required": True}
    response = value.get("response")
    if isinstance(response, dict):
        if isinstance(response.get("platform_post_id"), int): checkpoint["platform_post_id"] = response["platform_post_id"]
        if response.get("remote_status"): checkpoint["remote_status"] = response["remote_status"]
        if response.get("edit_url"): checkpoint["edit_url"] = response["edit_url"]
    return checkpoint


def _base_result(project_name: str, completed: list[str], lineage: dict[str, str], production: dict[str, Any], *, lifecycle: str, current: str | None, error: dict[str, str] | None, remaining: list[str] | None = None) -> dict[str, Any]:
    completed = list(dict.fromkeys(completed))
    remaining = [stage for stage in STAGES if stage not in completed] if remaining is None else list(dict.fromkeys(remaining))
    return {"orchestration_id": _orchestration_id(project_name, completed, lineage), "project_name": project_name, "schema_version": SCHEMA_VERSION, "lifecycle_stage": lifecycle, "current_stage": current, "completed_stages": completed, "remaining_stages": remaining, "lineage": lineage, "production": production, "error": error, "audit": {"method": "irl_production_orchestrator", "version": METHOD_VERSION, "validation_status": "failed" if lifecycle == "failed" else "validated"}}


def _production_template(context: dict[str, Any]) -> dict[str, Any]:
    production = context.get("production") if isinstance(context.get("production"), dict) else {}
    return {"assembly": copy.deepcopy(production.get("assembly", {})), "package": copy.deepcopy(production.get("package", {})), "boundary": copy.deepcopy(production.get("boundary", {})), "wordpress": copy.deepcopy(production.get("wordpress", {}))}


def _merge_stage_output(context: dict[str, Any], output: dict[str, Any], stage: str) -> None:
    context.update(output)
    production = _production_template(context)
    supplied = output.get("production")
    if isinstance(supplied, dict):
        for checkpoint in production:
            if isinstance(supplied.get(checkpoint), dict): production[checkpoint].update(copy.deepcopy(supplied[checkpoint]))
    if stage == "production_assembly" and isinstance(output.get("production_assembly"), dict) and {"assembly_id", "lifecycle_stage"} <= output["production_assembly"].keys(): production["assembly"] = _checkpoint_from_assembly(output["production_assembly"])
    if stage == "article_package" and isinstance(output.get("article_package"), dict) and isinstance(output["article_package"].get("identity"), dict): production["package"] = _checkpoint_from_package(output["article_package"])
    if stage == "production_delivery_boundary" and isinstance(output.get("production_delivery_boundary"), dict) and {"delivery_id", "lifecycle_stage", "delivery_status"} <= output["production_delivery_boundary"].keys(): production["boundary"] = _checkpoint_from_boundary(output["production_delivery_boundary"])
    if stage == "wordpress_delivery" and isinstance(output.get("wordpress_delivery"), dict): production["wordpress"] = _checkpoint_from_wordpress(output["wordpress_delivery"], live=output["wordpress_delivery"].get("execution_mode") == "live")
    context["production"] = production


def _terminal_lifecycle(context: dict[str, Any]) -> str:
    wordpress = _production_template(context)["wordpress"]
    if wordpress.get("execution_mode") == "live" and wordpress.get("delivery_status") == "delivered" and wordpress.get("remote_status") == "draft" and wordpress.get("publish") is False and wordpress.get("human_approval_required") is True: return "human_review"
    return "completed"


def build_production_orchestration(*, project_name: str, result: dict[str, Any], deliver: bool = False, connection: Any = None, transport: Callable[..., Any] | None = None, delivery_mode: str = "live") -> dict[str, Any]:
    """Coordinate the canonical production chain; O5 QA-only behavior remains unchanged when deliver=False."""
    if delivery_mode not in DELIVERY_MODES: raise ValueError(f"Unsupported delivery_mode: {delivery_mode}")
    context = copy.deepcopy(result)
    completed = [stage for stage in STAGES[:10] if stage in _completed_stages(context)]
    lineage = _lineage_from_result(context)
    production = _production_template(context)
    if not deliver:
        if "qa" in completed:
            return _base_result(project_name, completed, lineage, production, lifecycle="completed", current=None, error=None, remaining=[])
        current = next((stage for stage in STAGES[:10] if stage not in completed), None)
        return _base_result(project_name, completed, lineage, production, lifecycle="running", current=current, error=None)

    stage = "production_assembly"
    try:
        assembly = build_production_assembly(project_name=project_name, artifacts=_canonical_artifacts(context))
        production["assembly"] = _checkpoint_from_assembly(assembly)
        completed.append("production_assembly")
        stage = "article_package"
        package = build_article_package(project_name=project_name, artifacts=assembly["artifacts"], target_stage="delivery_ready")
        production["package"] = _checkpoint_from_package(package)
        completed.append("article_package")
        stage = "production_delivery_boundary"
        boundary = build_production_delivery_boundary(package=package, publisher_id="wordpress_publisher_v1", adapter_id="wordpress_delivery_adapter_v1", execution_mode=delivery_mode)
        production["boundary"] = _checkpoint_from_boundary(boundary)
        completed.append("production_delivery_boundary")
        if delivery_mode == "dry_run":
            production["wordpress"] = _checkpoint_from_wordpress({}, live=False)
            return _base_result(project_name, completed, lineage, production, lifecycle="completed", current=None, error=None, remaining=[])
        stage = "wordpress_delivery"
        wordpress = deliver_wordpress_delivery_boundary(boundary=boundary, connection=connection, transport=transport)
        production["wordpress"] = _checkpoint_from_wordpress(wordpress, live=True)
        completed.append("wordpress_delivery")
        return _base_result(project_name, completed, lineage, production, lifecycle="human_review", current=None, error=None, remaining=[])
    except Exception as exc:
        return _base_result(project_name, completed, lineage, production, lifecycle="failed", current=stage, error={"stage": stage, "type": type(exc).__name__, "message": str(exc)})


def _completed_stages(result: dict[str, Any]) -> list[str]:
    detected: set[str] = set()
    if isinstance(result.get("research_report"), dict): detected.add("research")
    if isinstance(result.get("content_brief"), dict): detected.update({"intelligence", "configuration", "structure"})
    if isinstance(result.get("article_draft"), dict): detected.add("draft")
    if isinstance(result.get("editorial_review"), dict): detected.add("editorial_cleanup")
    if isinstance(result.get("media", result.get("media_strategy")), dict): detected.add("media")
    if isinstance(result.get("linking"), dict) or "internal_linking" in result or "external_linking" in result: detected.add("linking")
    if isinstance(result.get("seo_validation", result.get("optimization")), dict): detected.add("optimization")
    if isinstance(result.get("article_draft_quality"), dict) and isinstance(result.get("claim_audit"), dict) and result.get("publication", {}).get("gate_status") == "allowed": detected.add("qa")
    return [stage for stage in STAGES[:10] if stage in detected]


def run_production_orchestrator(project_name: str, *, llm_provider: Any, deliver: bool = False, connection: Any = None, transport: Callable[..., Any] | None = None, delivery_mode: str = "live") -> dict[str, Any]:
    """Coordinate upstream content production and, when requested, the canonical controlled production chain."""
    result = run_content_research_to_wordpress_draft(project_name, llm_provider=llm_provider, deliver=False, connection=connection, transport=transport)
    return build_production_orchestration(project_name=project_name, result=result, deliver=deliver, connection=connection, transport=transport, delivery_mode=delivery_mode)


def execute_stage_plan(*, project_name: str, stage_runner: StageRunner, start_stage: str = "research", initial_outputs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute canonical stage boundaries with fail-stop and controlled resume semantics."""
    if start_stage not in STAGES: raise ValueError(f"Unknown production stage: {start_stage}")
    context: dict[str, Any] = copy.deepcopy(initial_outputs or {})
    completed = [stage for stage in STAGES if stage in context.get("completed_stages", [])]
    start_index = STAGES.index(start_stage)
    required_prefix = list(STAGES[:start_index])
    if required_prefix and not all(stage in completed for stage in required_prefix): raise ValueError("Resume requires all earlier stage checkpoints to be supplied")
    for stage in STAGES[start_index:]:
        try:
            output = stage_runner(stage, copy.deepcopy(context))
            if not isinstance(output, dict): raise TypeError("Stage runner must return a dictionary")
            _merge_stage_output(context, output, stage)
            if stage not in completed: completed.append(stage)
        except Exception as exc:
            return _base_result(project_name, completed, _lineage_from_result(context), _production_template(context), lifecycle="failed", current=stage, error={"stage": stage, "type": type(exc).__name__, "message": str(exc)})
    return _base_result(project_name, completed, _lineage_from_result(context), _production_template(context), lifecycle=_terminal_lifecycle(context), current=None, error=None)
