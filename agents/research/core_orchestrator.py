from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from .adaptive_recovery import plan_recoveries
from .content_research_pipeline import _load, run_content_research_to_wordpress_draft
from .recovery_executor import ClaimReviser, EditorialReviser, EvidenceAcquirer, RecoveryExecutionError, SectionReviser, SeoReviser, execute_recovery
from .recovery_verification import RecoveryVerificationError, verify_recovery
from .revision_planner import build_revision_plan
from .wordpress_draft_delivery_client import WordPressConnection

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v4"
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "shared" / "schemas" / "core-orchestration.schema.json"

RevisionHandler = Callable[[str, str, dict[str, Any], dict[str, Any], int], Any]
PipelineRunner = Callable[..., dict[str, Any]]


def _orchestration_id(project_name: str, state: dict[str, Any]) -> str:
    raw = json.dumps({"project_name": project_name, "state": state}, sort_keys=True, ensure_ascii=False)
    return f"core_orchestration_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _recovery_results(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    structured: dict[str, dict[str, Any]] = {}
    for gate in ("claim_audit", "article_draft_quality", "seo_validation", "editorial_review"):
        gate_result = result.get(gate)
        if not isinstance(gate_result, dict):
            continue
        if gate == "claim_audit" and isinstance(gate_result.get("claims"), list):
            structured[gate] = gate_result
        elif gate != "claim_audit" and isinstance(gate_result.get("findings"), list) and gate_result.get("findings"):
            structured[gate] = gate_result
    return structured


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


def _executor_compatible_plan(*, plan: dict[str, Any], claim_reviser: ClaimReviser | None, evidence_acquirer: EvidenceAcquirer | None) -> dict[str, Any]:
    """Adapt an evidence-first disputed-claim plan when only claim revision is executable.

    The recovery planner remains authoritative: disputed claims continue to plan
    ``acquire_evidence``. The bounded revision loop may use ``revise_claim`` as
    an execution fallback when the caller explicitly supplied a claim reviser
    but no evidence acquirer. Verification follows the executed strategy.
    """
    if plan.get("strategy") != "acquire_evidence" or evidence_acquirer is not None or claim_reviser is None:
        return plan
    adapted = dict(plan)
    adapted["strategy"] = "revise_claim"
    adapted["actions"] = ["Revise the targeted claim using the available recovery executor.", "Preserve evidence lineage while revising the claim."]
    adapted["rerun_gates"] = ["article_draft_quality", "claim_audit"]
    adapted["rationale"] = "The disputed claim has no evidence-acquisition executor available; use the explicitly supplied claim reviser as the bounded fallback."
    return adapted


def build_orchestration_result(*, project_name: str, result: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    next_action, rationale = _decision_action(result=result, decision=decision)
    gates = {"article_draft_quality": result.get("article_draft_quality", {}).get("outcome"), "claim_audit": result.get("claim_audit", {}).get("outcome"), "seo_validation": result.get("seo_validation", {}).get("outcome"), "editorial_review": result.get("editorial_review", {}).get("outcome"), "publication": result.get("publication", {}).get("gate_status"), "wordpress_delivery": result.get("wordpress_draft_delivery_result", {}).get("remote_status")}
    revision_plan = build_revision_plan(result=result)
    adaptive_recovery = plan_recoveries(results=_recovery_results(result))
    stopped_recoveries = [plan for plan in adaptive_recovery if plan["status"] == "stopped"]
    if stopped_recoveries:
        first = stopped_recoveries[0]
        next_action = "stop"
        rationale = first["rationale"]
    elif adaptive_recovery and next_action not in {"stop", "complete"}:
        first = adaptive_recovery[0]
        next_action = first["strategy"]
        rationale = first["rationale"]
    lifecycle_stage = "completed" if next_action == "complete" else "blocked" if next_action == "stop" else "action_required"
    state = {"lifecycle_stage": lifecycle_stage, "next_action": next_action, "gates": gates, "decision_outcome": decision.get("outcome"), "revision_plan_outcome": revision_plan["outcome"], "adaptive_recovery_count": len(adaptive_recovery)}
    return {"orchestration_id": _orchestration_id(project_name, state), "project_name": project_name, "schema_version": SCHEMA_VERSION, "lifecycle_stage": lifecycle_stage, "current_stage": next_action, "stage": next_action, "next_action": next_action, "decision_outcome": decision.get("outcome"), "outcome": "complete" if next_action == "complete" else "blocked" if next_action == "stop" else "action_required", "reason": rationale, "rationale": [rationale], "gates": gates, "revision_plan": revision_plan, "adaptive_recovery": {"outcome": "stopped" if stopped_recoveries else "planned" if adaptive_recovery else "not_required", "plans": adaptive_recovery, "summary": {"total": len(adaptive_recovery), "stopped": len(stopped_recoveries), "planned": sum(plan["status"] == "planned" for plan in adaptive_recovery)}}, "audit": {"method": "irl_core_decision_orchestrator", "version": METHOD_VERSION, "validation_status": "validated"}}


def run_irl_core(project_name: str, *, deliver: bool = False, connection: WordPressConnection | None = None, transport: Callable[..., Any] | None = None) -> dict[str, Any]:
    result = run_content_research_to_wordpress_draft(project_name, deliver=deliver, connection=connection, transport=transport)
    decision = _load(project_name, "decision.json")
    result["core_orchestration"] = build_orchestration_result(project_name=project_name, result=result, decision=decision)
    return result


def run_core_orchestration(project_name: str, *, deliver: bool = True, connection: WordPressConnection | None = None, transport: Callable[..., Any] | None = None) -> dict[str, Any]:
    return run_irl_core(project_name, deliver=deliver, connection=connection, transport=transport)["core_orchestration"]


def run_revision_loop(project_name: str, *, deliver: bool = True, connection: WordPressConnection | None = None, transport: Callable[..., Any] | None = None, pipeline_runner: PipelineRunner | None = None, revision_handler: RevisionHandler | None = None, max_iterations: int = 3, evidence_acquirer: EvidenceAcquirer | None = None, claim_reviser: ClaimReviser | None = None, section_reviser: SectionReviser | None = None, seo_reviser: SeoReviser | None = None, editorial_reviser: EditorialReviser | None = None) -> dict[str, Any]:
    """Run bounded autonomous revision with executable recovery strategies."""
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1")
    runner = pipeline_runner or run_content_research_to_wordpress_draft
    history: list[dict[str, Any]] = []
    result: dict[str, Any] | None = None
    pending_verification: dict[str, Any] | None = None
    pending_history_index: int | None = None
    for iteration in range(1, max_iterations + 1):
        result = runner(project_name, deliver=deliver, connection=connection, transport=transport)
        verification: dict[str, Any] | None = None
        if pending_verification is not None:
            try:
                verification = verify_recovery(plan=pending_verification, result=result)
            except RecoveryVerificationError as exc:
                verification = {"recovery_id": pending_verification.get("recovery_id", ""), "strategy": pending_verification.get("strategy", ""), "status": "failed", "passed": False, "checks": [], "failed_gates": [], "error": str(exc)}
            if pending_history_index is not None and 0 <= pending_history_index < len(history):
                history[pending_history_index]["recovery_verification"] = verification
            pending_verification = None
            pending_history_index = None
        decision = _load(project_name, "decision.json")
        orchestration = build_orchestration_result(project_name=project_name, result=result, decision=decision)
        action = orchestration["next_action"]
        revision_count = iteration - 1
        orchestration["iterations"] = revision_count
        history_entry = {"iteration": iteration, "action": action, "outcome": orchestration["outcome"], "reason": orchestration["reason"], "gates": orchestration["gates"], "revision_plan": orchestration["revision_plan"], "adaptive_recovery": orchestration["adaptive_recovery"]}
        history.append(history_entry)
        if verification is not None and not verification["passed"] and action == "complete":
            action = orchestration["next_action"] = "stop"
            orchestration["outcome"] = "blocked"
            orchestration["reason"] = "Recovery verification failed after the required gate re-run."
            history_entry["action"] = action
            history_entry["outcome"] = orchestration["outcome"]
            history_entry["reason"] = orchestration["reason"]
        if action in {"complete", "stop"}:
            if verification is not None and history:
                for entry in reversed(history):
                    if "recovery_execution" in entry:
                        entry["recovery_verification"] = verification
                        break
            orchestration["revision_loop"] = {"status": "completed" if action == "complete" else "stopped", "iterations": iteration, "revision_count": revision_count, "max_iterations": max_iterations, "history": history}
            result["core_orchestration"] = orchestration
            return orchestration
        if action == "deliver_wordpress_draft":
            if not deliver or iteration == max_iterations:
                orchestration["revision_loop"] = {"status": "stopped" if not deliver else "revision_limit_reached", "iterations": iteration, "revision_count": revision_count, "max_iterations": max_iterations, "history": history}
                result["core_orchestration"] = orchestration
                return orchestration
            continue
        recovery_plan = next((plan for plan in orchestration["adaptive_recovery"]["plans"] if plan["strategy"] == action), None)
        recovery_plan = _executor_compatible_plan(plan=recovery_plan, claim_reviser=claim_reviser, evidence_acquirer=evidence_acquirer) if recovery_plan is not None else None
        if recovery_plan is not None:
            action = recovery_plan["strategy"]
            orchestration["next_action"] = action
            history_entry["action"] = action
        executable_strategy = action in {"acquire_evidence", "revise_claim", "revise_section", "revise_seo", "revise_editorial"}
        callback_available = ((action == "acquire_evidence" and evidence_acquirer is not None) or (action == "revise_claim" and claim_reviser is not None) or (action == "revise_section" and section_reviser is not None) or (action == "revise_seo" and seo_reviser is not None) or (action == "revise_editorial" and editorial_reviser is not None))
        if executable_strategy and callback_available and recovery_plan is not None:
            try:
                execution = execute_recovery(project_name=project_name, result=result, plan=recovery_plan, evidence_acquirer=evidence_acquirer, claim_reviser=claim_reviser, section_reviser=section_reviser, seo_reviser=seo_reviser, editorial_reviser=editorial_reviser)
            except RecoveryExecutionError as exc:
                history_entry["recovery_execution"] = {"strategy": action, "status": "failed", "error": str(exc)}
                orchestration["revision_loop"] = {"status": "stopped", "iterations": iteration, "revision_count": revision_count, "max_iterations": max_iterations, "history": history}
                result["core_orchestration"] = orchestration
                return orchestration
            history_entry["recovery_execution"] = execution
            pending_verification = recovery_plan
            pending_history_index = len(history) - 1
            if iteration == max_iterations:
                orchestration["revision_loop"] = {"status": "revision_limit_reached", "iterations": iteration, "revision_count": revision_count, "max_iterations": max_iterations, "history": history}
                result["core_orchestration"] = orchestration
                return orchestration
            continue
        if iteration == max_iterations or revision_handler is None:
            orchestration["revision_loop"] = {"status": "revision_limit_reached" if iteration == max_iterations else "handler_required", "iterations": iteration, "revision_count": revision_count, "max_iterations": max_iterations, "history": history}
            result["core_orchestration"] = orchestration
            return orchestration
        revision_handler(project_name, action, result, orchestration, iteration)
    raise RuntimeError("Revision loop terminated without a result")
