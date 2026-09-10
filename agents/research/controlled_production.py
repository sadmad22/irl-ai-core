from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

from .production_orchestrator import run_production_orchestrator
from .wordpress_connector import deliver_wordpress_draft_from_production

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

STATUSES = (
    "queued",
    "running",
    "ready_for_delivery",
    "draft_delivered",
    "human_review",
    "approved",
    "rejected",
    "failed",
)

_ALLOWED_TRANSITIONS = {
    "queued": {"running", "failed"},
    "running": {"running", "ready_for_delivery", "failed"},
    "ready_for_delivery": {"draft_delivered", "failed"},
    "draft_delivered": {"human_review", "failed"},
    "human_review": {"approved", "rejected", "failed"},
    "approved": {"approved"},
    "rejected": {"rejected"},
    "failed": {"failed"},
}


def _run_id(project_name: str, topic: str, production_id: str) -> str:
    raw = json.dumps(
        {"project_name": project_name, "topic": topic, "production_id": production_id, "schema_version": SCHEMA_VERSION},
        sort_keys=True,
        ensure_ascii=False,
    )
    return f"run_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _audit() -> dict[str, str]:
    return {
        "method": "controlled_production",
        "version": METHOD_VERSION,
        "validation_status": "validated",
    }


def _error(error_type: str, message: str) -> dict[str, str]:
    return {"type": str(error_type).strip(), "message": str(message).strip()}


def create_controlled_production_run(
    *,
    project_name: str,
    topic: str,
    production_id: str,
    orchestration_id: str,
) -> dict[str, Any]:
    project = str(project_name).strip()
    topic_value = str(topic).strip()
    production = str(production_id).strip()
    orchestration = str(orchestration_id).strip()

    if not project:
        raise ValueError("project_name is required")
    if not topic_value:
        raise ValueError("topic is required")
    if not re.fullmatch(r"production_[a-f0-9]{16}", production):
        raise ValueError("production_id must match ^production_[a-f0-9]{16}$")
    if not re.fullmatch(r"orchestration_[a-f0-9]{16}", orchestration):
        raise ValueError("orchestration_id must match ^orchestration_[a-f0-9]{16}$")

    return {
        "run_id": _run_id(project, topic_value, production),
        "schema_version": SCHEMA_VERSION,
        "project_name": project,
        "topic": topic_value,
        "production_id": production,
        "orchestration_id": orchestration,
        "status": "queued",
        "error": None,
        "delivery": {
            "status": "not_started",
            "delivery_id": None,
            "post_id": None,
            "edit_url": None,
            "remote_status": None,
            "error": None,
        },
        "human_review": {"required": True, "status": "pending"},
        "publication": {"mode": "wordpress_draft", "publish": False, "human_approval_required": True},
        "audit": _audit(),
    }


def transition_controlled_production_run(run: dict[str, Any], *, status: str) -> dict[str, Any]:
    if not isinstance(run, dict):
        raise TypeError("run must be a dictionary")
    previous = str(run.get("status", ""))
    if previous not in _ALLOWED_TRANSITIONS:
        raise ValueError(f"Invalid existing controlled production status: {previous}")
    if status not in _ALLOWED_TRANSITIONS[previous]:
        raise ValueError(f"Invalid controlled production transition: {previous} -> {status}")

    if status == "draft_delivered":
        delivery = run.get("delivery")
        if not isinstance(delivery, dict) or delivery.get("status") != "delivered" or delivery.get("remote_status") != "draft":
            raise ValueError("draft_delivered requires a delivered WordPress draft")
        if not isinstance(delivery.get("post_id"), int) or delivery["post_id"] < 1:
            raise ValueError("draft_delivered requires a valid WordPress post_id")

    if status == "human_review":
        delivery = run.get("delivery")
        if not isinstance(delivery, dict) or delivery.get("status") != "delivered" or delivery.get("remote_status") != "draft":
            raise ValueError("human_review requires a delivered WordPress draft")

    if status == "approved" and run.get("human_review", {}).get("status") != "pending":
        raise ValueError("approved requires pending human_review state")

    updated = dict(run)
    updated["status"] = status
    if status == "approved":
        updated["human_review"] = {"required": True, "status": "approved"}
    elif status == "rejected":
        if run.get("human_review", {}).get("status") != "pending":
            raise ValueError("rejected requires pending human_review state")
        updated["human_review"] = {"required": True, "status": "rejected"}
    elif status == "human_review":
        updated["human_review"] = {"required": True, "status": "pending"}
    updated["audit"] = _audit()
    return updated


def mark_controlled_production_failed(
    run: dict[str, Any],
    *,
    error_type: str,
    message: str,
) -> dict[str, Any]:
    if run.get("status") in {"approved", "rejected", "failed"}:
        raise ValueError("Cannot fail a terminal controlled production run")
    if not str(error_type).strip() or not str(message).strip():
        raise ValueError("error_type and message are required")
    updated = dict(run)
    updated["status"] = "failed"
    updated["error"] = _error(error_type, message)
    updated["audit"] = _audit()
    return updated


def run_controlled_production(
    project_name: str,
    *,
    topic: str,
    deliver: bool = False,
    connection: Any = None,
    transport: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run one controlled production cycle without permitting WordPress publication."""
    run = None
    try:
        run = {
            "run_id": "run_pending",
            "schema_version": SCHEMA_VERSION,
            "project_name": str(project_name).strip(),
            "topic": str(topic).strip(),
            "production_id": "production_pending",
            "orchestration_id": "orchestration_pending",
            "status": "queued",
            "error": None,
            "delivery": {
                "status": "not_started",
                "delivery_id": None,
                "post_id": None,
                "edit_url": None,
                "remote_status": None,
                "error": None,
            },
            "human_review": {"required": True, "status": "pending"},
            "publication": {"mode": "wordpress_draft", "publish": False, "human_approval_required": True},
            "audit": _audit(),
        }
        orchestration = run_production_orchestrator(project_name, deliver=False, connection=None, transport=None)
        package = orchestration.get("article_package")
        if not isinstance(package, dict):
            raise ValueError("Production orchestrator did not return an article package")
        production_id = str(package.get("production_id", "")).strip()
        orchestration_id = str(orchestration.get("orchestration_id", "")).strip()
        run = create_controlled_production_run(
            project_name=project_name,
            topic=topic,
            production_id=production_id,
            orchestration_id=orchestration_id,
        )
        run = transition_controlled_production_run(run, status="running")
        if orchestration.get("lifecycle_stage") != "completed":
            return mark_controlled_production_failed(
                run,
                error_type="ProductionOrchestrationIncomplete",
                message="Production orchestrator did not complete the article package.",
            )
        run = transition_controlled_production_run(run, status="ready_for_delivery")
        if not deliver:
            return run

        connector = deliver_wordpress_draft_from_production(package, connection=connection, transport=transport)
        response = connector.get("response")
        if not isinstance(response, dict) or response.get("delivery_status") != "delivered":
            return mark_controlled_production_failed(
                run,
                error_type="WordPressDeliveryFailed",
                message="WordPress draft delivery did not return a delivered response.",
            )
        run["delivery"] = {
            "status": "delivered",
            "delivery_id": str(connector.get("connector_id")),
            "post_id": response.get("post_id"),
            "edit_url": response.get("edit_url"),
            "remote_status": response.get("remote_status"),
            "error": response.get("error"),
        }
        run = transition_controlled_production_run(run, status="draft_delivered")
        return transition_controlled_production_run(run, status="human_review")
    except Exception as exc:
        if run is None or not re.fullmatch(r"run_[a-f0-9]{16}", str(run.get("run_id", ""))):
            raise
        return mark_controlled_production_failed(
            run,
            error_type=type(exc).__name__,
            message=str(exc),
        )
