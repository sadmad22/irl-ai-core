from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"


def _stabilization_id(project_name: str, production_id: str, orchestration_id: str, job_id: str, run_id: str) -> str:
    raw = json.dumps(
        {
            "project_name": project_name,
            "production_id": production_id,
            "orchestration_id": orchestration_id,
            "job_id": job_id,
            "run_id": run_id,
            "schema_version": SCHEMA_VERSION,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return f"stabilization_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _check(status: str, message: str) -> dict[str, str]:
    return {"status": status, "message": message}


def _required_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a dictionary")
    return value


def _required_id(value: Any, pattern: str, name: str) -> str:
    identifier = str(value or "").strip()
    if not re.fullmatch(pattern, identifier):
        raise ValueError(f"{name} must match {pattern}")
    return identifier


def _audit() -> dict[str, str]:
    return {
        "method": "production_stabilization",
        "version": METHOD_VERSION,
        "validation_status": "validated",
    }


def run_production_stabilization_audit(
    *,
    project_name: str,
    article_package: dict[str, Any],
    orchestration: dict[str, Any],
    production_job: dict[str, Any],
    controlled_production: dict[str, Any],
) -> dict[str, Any]:
    """Validate existing production records without mutating or executing them."""
    project = str(project_name).strip()
    if not project:
        raise ValueError("project_name is required")

    package = _required_dict(article_package, "article_package")
    orchestration_record = _required_dict(orchestration, "orchestration")
    job = _required_dict(production_job, "production_job")
    controlled = _required_dict(controlled_production, "controlled_production")

    production_id = _required_id(package.get("production_id"), r"production_[a-f0-9]{16}", "production_id")
    orchestration_id = _required_id(orchestration_record.get("orchestration_id"), r"orchestration_[a-f0-9]{16}", "orchestration_id")
    job_id = _required_id(job.get("job_id"), r"job_[a-f0-9]{16}", "job_id")
    run_id = _required_id(controlled.get("run_id"), r"run_[a-f0-9]{16}", "run_id")

    checks: dict[str, dict[str, str]] = {}

    package_publication = package.get("publication")
    package_ok = (
        package.get("lifecycle_stage") == "production_ready"
        and isinstance(package_publication, dict)
        and package_publication.get("mode") == "wordpress_draft"
        and package_publication.get("publish") is False
        and package_publication.get("human_approval_required") is True
    )
    checks["article_package"] = _check(
        "passed" if package_ok else "failed",
        "Article Package is production_ready and satisfies the draft-only publication contract."
        if package_ok
        else "Article Package is incomplete or violates the draft-only publication contract.",
    )

    orchestration_ok = (
        orchestration_record.get("project_name") == project
        and orchestration_record.get("lifecycle_stage") == "completed"
        and isinstance(orchestration_record.get("article_package"), dict)
        and orchestration_record.get("error") is None
        and str(orchestration_record.get("article_package", {}).get("production_id", "")).strip() == production_id
    )
    checks["orchestration"] = _check(
        "passed" if orchestration_ok else "failed",
        "Production Orchestrator is completed and points to the same Article Package."
        if orchestration_ok
        else "Production Orchestrator is incomplete, errored, or points to a different Article Package.",
    )

    lineage = job.get("lineage")
    job_ok = (
        job.get("lineage", {}).get("project_name") == project
        if isinstance(lineage, dict)
        else False
    )
    if job_ok and isinstance(lineage, dict):
        job_ok = (
            lineage.get("production_id") == production_id
            and lineage.get("orchestration_id") == orchestration_id
            and job.get("status") == "ready"
            and job.get("current_stage") == "article_package"
        )
    checks["production_job"] = _check(
        "passed" if job_ok else "failed",
        "Production Job is ready at article_package and preserves production/orchestration lineage."
        if job_ok
        else "Production Job is not a consistent ready projection of the production lineage.",
    )

    controlled_project_ok = controlled.get("project_name") == project
    controlled_lineage_ok = (
        controlled.get("production_id") == production_id
        and controlled.get("orchestration_id") == orchestration_id
    )
    controlled_status = controlled.get("status")
    delivery = controlled.get("delivery")
    delivery_ok = True
    if controlled_status in {"draft_delivered", "human_review", "approved"}:
        delivery_ok = (
            isinstance(delivery, dict)
            and delivery.get("status") == "delivered"
            and isinstance(delivery.get("post_id"), int)
            and delivery.get("post_id") >= 1
            and delivery.get("remote_status") == "draft"
        )
    controlled_ok = controlled_project_ok and controlled_lineage_ok and controlled_status in {
        "ready_for_delivery",
        "draft_delivered",
        "human_review",
        "approved",
        "rejected",
    } and delivery_ok
    checks["controlled_production"] = _check(
        "passed" if controlled_ok else "failed",
        "Controlled Production preserves lineage and, when delivered, confirms a WordPress draft."
        if controlled_ok
        else "Controlled Production is failed, inconsistent, or reports an invalid delivery state.",
    )

    controlled_publication = controlled.get("publication")
    publication_ok = (
        isinstance(package_publication, dict)
        and package_publication.get("mode") == "wordpress_draft"
        and package_publication.get("publish") is False
        and package_publication.get("human_approval_required") is True
        and isinstance(controlled_publication, dict)
        and controlled_publication.get("mode") == "wordpress_draft"
        and controlled_publication.get("publish") is False
        and controlled_publication.get("human_approval_required") is True
    )
    checks["publication_boundary"] = _check(
        "passed" if publication_ok else "failed",
        "Publication remains WordPress draft-only; human approval does not authorize publication."
        if publication_ok
        else "Publication boundary is inconsistent with the draft-only safety contract.",
    )

    outcome = "passed" if all(item["status"] == "passed" for item in checks.values()) else "blocked"
    return {
        "stabilization_id": _stabilization_id(project, production_id, orchestration_id, job_id, run_id),
        "schema_version": SCHEMA_VERSION,
        "project_name": project,
        "production_id": production_id,
        "orchestration_id": orchestration_id,
        "job_id": job_id,
        "run_id": run_id,
        "outcome": outcome,
        "checks": checks,
        "audit": _audit(),
    }
