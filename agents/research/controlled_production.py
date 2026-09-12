from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

from .production_orchestrator import run_production_orchestrator

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
STATUSES = ("queued", "running", "ready_for_delivery", "draft_delivered", "human_review", "approved", "rejected", "failed")
_ALLOWED_TRANSITIONS = {"queued": {"running", "failed"}, "running": {"running", "ready_for_delivery", "failed"}, "ready_for_delivery": {"draft_delivered", "failed"}, "draft_delivered": {"human_review", "failed"}, "human_review": {"approved", "rejected", "failed"}, "approved": {"approved"}, "rejected": {"rejected"}, "failed": {"failed"}}


def _run_id(project_name: str, production_id: str) -> str:
    raw = json.dumps({"project_name": project_name, "production_id": production_id, "schema_version": SCHEMA_VERSION}, sort_keys=True, ensure_ascii=False)
    return f"run_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _production_id_from_lineage(lineage: dict[str, Any]) -> str:
    draft_id = str(lineage.get("draft_id", "")).strip()
    quality_id = str(lineage.get("quality_id", "")).strip()
    if not draft_id or not quality_id:
        raise ValueError("Controlled Production requires draft_id and quality_id lineage")
    raw = json.dumps({"draft_id": draft_id, "quality_id": quality_id, "schema_version": "1.0"}, sort_keys=True, ensure_ascii=False)
    return f"production_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _audit() -> dict[str, str]:
    return {"method": "controlled_production", "version": METHOD_VERSION, "validation_status": "validated"}


def _error(error_type: str, message: str) -> dict[str, str]:
    return {"type": str(error_type).strip(), "message": str(message).strip()}


def create_controlled_production_run(*, project_name: str, production_id: str, orchestration_id: str) -> dict[str, Any]:
    project, production, orchestration = str(project_name).strip(), str(production_id).strip(), str(orchestration_id).strip()
    if not project: raise ValueError("project_name is required")
    if not re.fullmatch(r"production_[a-f0-9]{16}", production): raise ValueError("production_id must match ^production_[a-f0-9]{16}$")
    if not re.fullmatch(r"orchestration_[a-f0-9]{16}", orchestration): raise ValueError("orchestration_id must match ^orchestration_[a-f0-9]{16}$")
    return {"run_id": _run_id(project, production), "schema_version": SCHEMA_VERSION, "project_name": project, "production_id": production, "orchestration_id": orchestration, "status": "queued", "production_checkpoints": {"assembly_id": None, "package_id": None, "delivery_id": None}, "delivery": {"status": "not_started", "delivery_id": None, "post_id": None, "edit_url": None, "remote_status": None, "error": None}, "human_review": {"required": True, "status": "pending"}, "publication": {"mode": "wordpress_draft", "publish": False, "human_approval_required": True}, "audit": _audit()}


def transition_controlled_production_run(run: dict[str, Any], *, status: str) -> dict[str, Any]:
    if not isinstance(run, dict): raise TypeError("run must be a dictionary")
    previous = str(run.get("status", ""))
    if previous not in _ALLOWED_TRANSITIONS: raise ValueError(f"Invalid existing controlled production status: {previous}")
    if status not in _ALLOWED_TRANSITIONS[previous]: raise ValueError(f"Invalid controlled production transition: {previous} -> {status}")
    if status == "ready_for_delivery":
        checkpoints = run.get("production_checkpoints")
        if not isinstance(checkpoints, dict) or not all(str(checkpoints.get(key, "")).strip() for key in ("assembly_id", "package_id", "delivery_id")):
            raise ValueError("ready_for_delivery requires canonical production checkpoints")
    if status == "draft_delivered":
        delivery = run.get("delivery")
        if not isinstance(delivery, dict) or delivery.get("status") != "delivered" or delivery.get("remote_status") != "draft": raise ValueError("draft_delivered requires a delivered WordPress draft")
        if not isinstance(delivery.get("post_id"), int) or delivery["post_id"] < 1: raise ValueError("draft_delivered requires a valid WordPress post_id")
    if status == "human_review":
        delivery = run.get("delivery")
        if not isinstance(delivery, dict) or delivery.get("status") != "delivered" or delivery.get("remote_status") != "draft": raise ValueError("human_review requires a delivered WordPress draft")
    if status == "approved" and run.get("human_review", {}).get("status") != "pending": raise ValueError("approved requires pending human_review state")
    updated = dict(run); updated["status"] = status
    if status == "approved": updated["human_review"] = {"required": True, "status": "approved"}
    elif status == "rejected":
        if run.get("human_review", {}).get("status") != "pending": raise ValueError("rejected requires pending human_review state")
        updated["human_review"] = {"required": True, "status": "rejected"}
    elif status == "human_review": updated["human_review"] = {"required": True, "status": "pending"}
    updated["audit"] = _audit()
    return updated


def mark_controlled_production_failed(run: dict[str, Any], *, error_type: str, message: str) -> dict[str, Any]:
    if run.get("status") in {"approved", "rejected", "failed"}: raise ValueError("Cannot fail a terminal controlled production run")
    if not str(error_type).strip() or not str(message).strip(): raise ValueError("error_type and message are required")
    updated = dict(run); updated["status"] = "failed"; updated["delivery"] = dict(updated.get("delivery", {})); updated["delivery"]["status"] = "failed"; updated["delivery"]["error"] = _error(error_type, message); updated["audit"] = _audit(); return updated


def _apply_production_checkpoints(run: dict[str, Any], orchestration: dict[str, Any]) -> None:
    production = orchestration.get("production")
    if not isinstance(production, dict): raise ValueError("Production orchestrator did not return canonical production checkpoints")
    assembly = production.get("assembly")
    package = production.get("package")
    boundary = production.get("boundary")
    if not isinstance(assembly, dict) or not str(assembly.get("assembly_id", "")).strip(): raise ValueError("Production Assembly checkpoint is missing")
    if not isinstance(package, dict) or not str(package.get("package_id", "")).strip(): raise ValueError("Article Package checkpoint is missing")
    if not isinstance(boundary, dict) or not str(boundary.get("delivery_id", "")).strip(): raise ValueError("Production Delivery Boundary checkpoint is missing")
    run["production_checkpoints"] = {"assembly_id": assembly["assembly_id"], "package_id": package["package_id"], "delivery_id": boundary["delivery_id"]}


def run_controlled_production(project_name: str, *, llm_provider: Any, deliver: bool = False, connection: Any = None, transport: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Run one canonical controlled production cycle without permitting WordPress publication."""
    run = None
    try:
        delivery_mode = "live" if deliver else "dry_run"
        orchestration = run_production_orchestrator(project_name, llm_provider=llm_provider, deliver=True, connection=connection, transport=transport, delivery_mode=delivery_mode)
        lineage = orchestration.get("lineage")
        if not isinstance(lineage, dict): raise ValueError("Production orchestrator did not return lineage")
        production_id = _production_id_from_lineage(lineage)
        orchestration_id = str(orchestration.get("orchestration_id", "")).strip()
        run = create_controlled_production_run(project_name=project_name, production_id=production_id, orchestration_id=orchestration_id)
        run = transition_controlled_production_run(run, status="running")
        if orchestration.get("lifecycle_stage") == "failed":
            error = orchestration.get("error") if isinstance(orchestration.get("error"), dict) else {}
            return mark_controlled_production_failed(run, error_type=str(error.get("type", "ProductionOrchestrationFailed")), message=str(error.get("message", "Canonical production orchestration failed.")))
        _apply_production_checkpoints(run, orchestration)
        if not deliver:
            return transition_controlled_production_run(run, status="ready_for_delivery")
        wordpress = orchestration.get("production", {}).get("wordpress")
        if not isinstance(wordpress, dict) or wordpress.get("execution_mode") != "live" or wordpress.get("delivery_status") != "delivered" or wordpress.get("remote_status") != "draft" or wordpress.get("publish") is not False or wordpress.get("human_approval_required") is not True:
            return mark_controlled_production_failed(run, error_type="WordPressDeliveryFailed", message="Canonical WordPress adapter did not return a delivered draft-only result.")
        post_id = wordpress.get("platform_post_id")
        if not isinstance(post_id, int) or post_id < 1: return mark_controlled_production_failed(run, error_type="WordPressDeliveryFailed", message="Canonical WordPress adapter did not return a valid post id.")
        run["delivery"] = {"status": "delivered", "delivery_id": run["production_checkpoints"]["delivery_id"], "post_id": post_id, "edit_url": wordpress.get("edit_url"), "remote_status": "draft", "error": None}
        run = transition_controlled_production_run(run, status="draft_delivered")
        return transition_controlled_production_run(run, status="human_review")
    except Exception as exc:
        if run is None or not re.fullmatch(r"run_[a-f0-9]{16}", str(run.get("run_id", ""))): raise
        return mark_controlled_production_failed(run, error_type=type(exc).__name__, message=str(exc))
