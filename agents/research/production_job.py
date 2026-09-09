from __future__ import annotations

import re
import uuid
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

STATUSES = (
    "queued",
    "researching",
    "building",
    "drafting",
    "editing",
    "optimizing",
    "qa",
    "ready",
    "published",
    "failed",
)

STAGES = (
    "research",
    "intelligence",
    "configuration",
    "structure",
    "draft",
    "editorial_cleanup",
    "media",
    "linking",
    "optimization",
    "qa",
    "article_package",
)

_STATUS_STAGES = {
    "queued": (None,),
    "researching": ("research",),
    "building": ("intelligence", "configuration", "structure"),
    "drafting": ("draft",),
    "editing": ("editorial_cleanup",),
    "optimizing": ("media", "linking", "optimization"),
    "qa": ("qa",),
    "ready": ("article_package",),
    "published": (None,),
    "failed": STAGES,
}

_ALLOWED_TRANSITIONS = {
    "queued": {"researching", "failed"},
    "researching": {"researching", "building", "failed"},
    "building": {"building", "drafting", "failed"},
    "drafting": {"drafting", "editing", "failed"},
    "editing": {"editing", "optimizing", "failed"},
    "optimizing": {"optimizing", "qa", "failed"},
    "qa": {"qa", "ready", "failed"},
    "ready": {"published", "ready"},
    "published": {"published"},
    "failed": {"failed"},
}


def _new_job_id() -> str:
    return f"job_{uuid.uuid4().hex[:16]}"


def _validate_stage_for_status(status: str, current_stage: str | None) -> None:
    if status not in STATUSES:
        raise ValueError(f"Unknown production job status: {status}")
    if current_stage not in _STATUS_STAGES[status]:
        raise ValueError(f"Invalid current_stage for status {status}: {current_stage}")


def _audit() -> dict[str, str]:
    return {
        "method": "production_job_state",
        "version": METHOD_VERSION,
        "validation_status": "validated",
    }


def create_production_job(
    project_name: str,
    *,
    job_id: str | None = None,
    orchestration_id: str | None = None,
    production_id: str | None = None,
) -> dict[str, Any]:
    """Create the initial trackable Production Job State."""
    project = str(project_name).strip()
    if not project:
        raise ValueError("project_name is required")

    identifier = job_id or _new_job_id()
    if not isinstance(identifier, str) or not re.fullmatch(r"job_[a-f0-9]{16}", identifier):
        raise ValueError("job_id must match ^job_[a-f0-9]{16}$")

    lineage: dict[str, str] = {"project_name": project}
    if orchestration_id is not None and str(orchestration_id).strip():
        lineage["orchestration_id"] = str(orchestration_id).strip()
    if production_id is not None and str(production_id).strip():
        lineage["production_id"] = str(production_id).strip()

    return {
        "job_id": identifier,
        "schema_version": SCHEMA_VERSION,
        "status": "queued",
        "current_stage": None,
        "lineage": lineage,
        "error": None,
        "ready_to_publish": False,
        "audit": _audit(),
    }


def advance_production_job(
    job: dict[str, Any],
    *,
    status: str,
    current_stage: str | None,
) -> dict[str, Any]:
    """Advance a job through the roadmap status machine without doing production work."""
    if not isinstance(job, dict):
        raise TypeError("job must be a dictionary")
    previous = str(job.get("status", ""))
    if previous not in _ALLOWED_TRANSITIONS:
        raise ValueError(f"Invalid existing production job status: {previous}")
    if status not in _ALLOWED_TRANSITIONS[previous]:
        raise ValueError(f"Invalid production job transition: {previous} -> {status}")
    _validate_stage_for_status(status, current_stage)

    updated = dict(job)
    updated["status"] = status
    updated["current_stage"] = current_stage
    updated["error"] = None if status != "failed" else job.get("error")
    updated["ready_to_publish"] = status == "ready"
    updated["audit"] = _audit()
    return updated


def fail_production_job(
    job: dict[str, Any],
    *,
    stage: str,
    error_type: str,
    message: str,
) -> dict[str, Any]:
    """Record the failed state while preserving the job lineage."""
    if stage not in STAGES:
        raise ValueError(f"Unknown production stage: {stage}")
    if not str(error_type).strip() or not str(message).strip():
        raise ValueError("error_type and message are required")
    if job.get("status") in {"published", "failed"}:
        raise ValueError("Cannot fail a terminal production job")

    updated = dict(job)
    updated["status"] = "failed"
    updated["current_stage"] = stage
    updated["error"] = {
        "stage": stage,
        "type": str(error_type).strip(),
        "message": str(message).strip(),
    }
    updated["ready_to_publish"] = False
    updated["audit"] = _audit()
    return updated


def job_from_orchestration(orchestration: dict[str, Any]) -> dict[str, Any]:
    """Project an existing Production Orchestrator record into Job State."""
    if not isinstance(orchestration, dict):
        raise TypeError("orchestration must be a dictionary")

    project = str(orchestration.get("project_name", "")).strip()
    if not project:
        raise ValueError("Orchestration project_name is required")
    orchestration_id = str(orchestration.get("orchestration_id", "")).strip() or None

    package = orchestration.get("article_package")
    production_id = str(package.get("production_id", "")).strip() if isinstance(package, dict) else None
    job = create_production_job(
        project,
        orchestration_id=orchestration_id,
        production_id=production_id or None,
    )

    lifecycle = orchestration.get("lifecycle_stage")
    if lifecycle == "failed":
        error = orchestration.get("error")
        if not isinstance(error, dict):
            raise ValueError("Failed orchestration must contain an error")
        return fail_production_job(
            job,
            stage=str(error.get("stage", "")).strip(),
            error_type=str(error.get("type", "ProductionError")),
            message=str(error.get("message", "Production job failed")),
        )

    if lifecycle == "completed":
        return _project_status(job, status="ready", current_stage="article_package")

    stage = orchestration.get("current_stage")
    if stage == "research":
        status = "researching"
    elif stage in {"intelligence", "configuration", "structure"}:
        status = "building"
    elif stage == "draft":
        status = "drafting"
    elif stage == "editorial_cleanup":
        status = "editing"
    elif stage in {"media", "linking", "optimization"}:
        status = "optimizing"
    elif stage == "qa":
        status = "qa"
    elif stage == "article_package":
        status = "ready"
    else:
        return job

    return _project_status(job, status=status, current_stage=stage)


def _project_status(
    job: dict[str, Any],
    *,
    status: str,
    current_stage: str | None,
) -> dict[str, Any]:
    """Project a previously executed orchestration status without simulating transitions."""
    _validate_stage_for_status(status, current_stage)
    updated = dict(job)
    updated["status"] = status
    updated["current_stage"] = current_stage
    updated["error"] = None
    updated["ready_to_publish"] = status == "ready"
    updated["audit"] = _audit()
    return updated
