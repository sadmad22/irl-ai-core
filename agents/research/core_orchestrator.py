from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from .content_research_pipeline import _load, run_content_research_to_wordpress_draft
from .revision_planner import build_revision_plan
from .wordpress_draft_delivery_client import WordPressConnection

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v3"
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "shared" / "schemas" / "core-orchestration.schema.json"

RevisionHandler = Callable[[str, str, dict[str, Any], dict[str, Any], int], Any]
PipelineRunner = Callable[..., dict[str, Any]]


def _orchestration_id(project_name: str, state: dict[str, Any]) -> str:
    raw = json.dumps({"project_name": project_name, "state": state}, sort_keys=True, ensure_ascii=False)
    return f"core_orchestration_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _decision_action(*, result: dict[str, Any], decision: dict[str, Any]) -> tuple[str, str]:
    if decision.get("outcome") != "approved":
        return "stop", "Decision Engine did not approve content production."
    if result.get("article_draft_quality", {}).get("outcome") != "passed":
        return "revise_article_draft", "Article Draft Quality Gate requires revision."
    if result.get("claim_audit", {}).get("outcome") != "passed":
        return "revise_claims", "Claim Audit requires revision before downstream processing."
    if result.get("seo_validation", {}).get("outcome") != "passed":
        return "revise_seo", "SEO Validation requires revision."
    if result.get("editorial_review", {}).get("outcome") != "approved":
        return "revise_editorial", "Editorial Review did not approve the draft."
    if result.get("publication", {}).get("gate_status") != "allowed":
        return "stop", "Publication Gate blocked delivery."
    delivery = result.get("wordpress_draft_delivery_result")
    if isinstance(delivery, dict) and delivery.get("remote_status") == "draft":
        return "complete", "WordPress draft delivered successfully."
    return "deliver_wordpress_draft", "Content is approved and ready for WordPress draft delivery."


def build_orchestration_result(*, project_name: str, result: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    next_action, rationale = _decision_action(result=result, decision=decision)
    gates = {
        "article_draft_quality": result.get("article_draft_quality", {}).get("outcome"),
        "claim_audit": result.get("claim_audit", {}).get("outcome"),
        "seo_validation": result.get("seo_validation", {}).get("outcome"),
        "editorial_review": result.get("editorial_review", {}).get("outcome"),
        "publication": result.get("publication", {}).get("gate_status"),
        "wordpress_delivery": result.get("wordpress_draft_delivery_result", {}).get("remote_status"),
    }
    revision_plan = build_revision_plan(result=result)
    lifecycle_stage = "completed" if next_action == "complete" else "blocked" if next_action == "stop" else "action_required"
    state = {"lifecycle_stage": lifecycle_stage, "next_action": next_action, "gates": gates, "decision_outcome": decision.get("outcome"), "revision_plan_outcome": revision_plan["outcome"]}
    return {
        "orchestration_id": _orchestration_id(project_name, state),
        "project_name": project_name,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": lifecycle_stage,
        "current_stage": next_action,
        "stage": next_action,
        "next_action": next_action,
        "decision_outcome": decision.get("outcome"),
        "outcome": "complete" if next_action == "complete" else "blocked" if next_action == "stop" else "action_required",
        "reason": rationale,
        "rationale": [rationale],
        "gates": gates,
        "revision_plan": revision_plan,
        "audit": {"method": "irl_core_decision_orchestrator", "version": METHOD_VERSION, "validation_status": "validated"},
    }


def run_irl_core(project_name: str, *, deliver: bool = False, connection: WordPressConnection | None = None, transport: Callable[..., Any] | None = None) -> dict[str, Any]:
    result = run_content_research_to_wordpress_draft(project_name, deliver=deliver, connection=connection, transport=transport)
    decision = _load(project_name, "decision.json")
    result["core_orchestration"] = build_orchestration_result(project_name=project_name, result=result, decision=decision)
    return result


def run_core_orchestration(project_name: str, *, deliver: bool = True, connection: WordPressConnection | None = None, transport: Callable[..., Any] | None = None) -> dict[str, Any]:
    return run_irl_core(project_name, deliver=deliver, connection=connection, transport=transport)["core_orchestration"]


def run_revision_loop(project_name: str, *, deliver: bool = True, connection: WordPressConnection | None = None, transport: Callable[..., Any] | None = None, pipeline_runner: PipelineRunner | None = None, revision_handler: RevisionHandler | None = None, max_iterations: int = 3) -> dict[str, Any]:
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1")
    runner = pipeline_runner or run_content_research_to_wordpress_draft
    history: list[dict[str, Any]] = []
    result: dict[str, Any] | None = None
    for iteration in range(1, max_iterations + 1):
        result = runner(project_name, deliver=deliver, connection=connection, transport=transport)
        decision = _load(project_name, "decision.json")
        orchestration = build_orchestration_result(project_name=project_name, result=result, decision=decision)
        action = orchestration["next_action"]
        revision_count = iteration - 1
        orchestration["iterations"] = revision_count
        history.append({"iteration": iteration, "action": action, "outcome": orchestration["outcome"], "reason": orchestration["reason"], "gates": orchestration["gates"], "revision_plan": orchestration["revision_plan"]})
        if action in {"complete", "stop"}:
            orchestration["revision_loop"] = {"status": "completed" if action == "complete" else "stopped", "iterations": iteration, "revision_count": revision_count, "max_iterations": max_iterations, "history": history}
            result["core_orchestration"] = orchestration
            return orchestration
        if action == "deliver_wordpress_draft":
            if not deliver or iteration == max_iterations:
                orchestration["revision_loop"] = {"status": "stopped" if not deliver else "revision_limit_reached", "iterations": iteration, "revision_count": revision_count, "max_iterations": max_iterations, "history": history}
                result["core_orchestration"] = orchestration
                return orchestration
            continue
        if iteration == max_iterations or revision_handler is None:
            orchestration["revision_loop"] = {"status": "revision_limit_reached" if iteration == max_iterations else "handler_required", "iterations": iteration, "revision_count": revision_count, "max_iterations": max_iterations, "history": history}
            result["core_orchestration"] = orchestration
            return orchestration
        revision_handler(project_name, action, result, orchestration, iteration)
    raise RuntimeError("Revision loop terminated without a result")
