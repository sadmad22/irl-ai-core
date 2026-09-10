from __future__ import annotations

from copy import deepcopy

import pytest

from agents.research.production_stabilization import run_production_stabilization_audit


PRODUCTION_ID = "production_0123456789abcdef"
ORCHESTRATION_ID = "orchestration_0123456789abcdef"
JOB_ID = "job_0123456789abcdef"
RUN_ID = "run_0123456789abcdef"


def _records() -> tuple[dict, dict, dict, dict]:
    package = {
        "production_id": PRODUCTION_ID,
        "lifecycle_stage": "production_ready",
        "publication": {
            "mode": "wordpress_draft",
            "publish": False,
            "human_approval_required": True,
        },
    }
    orchestration = {
        "orchestration_id": ORCHESTRATION_ID,
        "project_name": "m7-consultant-liability",
        "lifecycle_stage": "completed",
        "article_package": {"production_id": PRODUCTION_ID},
        "error": None,
    }
    job = {
        "job_id": JOB_ID,
        "status": "ready",
        "current_stage": "article_package",
        "lineage": {
            "project_name": "m7-consultant-liability",
            "orchestration_id": ORCHESTRATION_ID,
            "production_id": PRODUCTION_ID,
        },
    }
    controlled = {
        "run_id": RUN_ID,
        "project_name": "m7-consultant-liability",
        "production_id": PRODUCTION_ID,
        "orchestration_id": ORCHESTRATION_ID,
        "status": "human_review",
        "delivery": {
            "status": "delivered",
            "post_id": 123,
            "remote_status": "draft",
        },
        "publication": {
            "mode": "wordpress_draft",
            "publish": False,
            "human_approval_required": True,
        },
    }
    return package, orchestration, job, controlled


def test_stabilization_passes_consistent_production_records() -> None:
    package, orchestration, job, controlled = _records()
    result = run_production_stabilization_audit(
        project_name="m7-consultant-liability",
        article_package=package,
        orchestration=orchestration,
        production_job=job,
        controlled_production=controlled,
    )
    assert result["outcome"] == "passed"
    assert all(check["status"] == "passed" for check in result["checks"].values())
    assert result["production_id"] == PRODUCTION_ID
    assert result["orchestration_id"] == ORCHESTRATION_ID
    assert result["job_id"] == JOB_ID
    assert result["run_id"] == RUN_ID


def test_stabilization_is_deterministic() -> None:
    package, orchestration, job, controlled = _records()
    first = run_production_stabilization_audit(
        project_name="m7-consultant-liability",
        article_package=package,
        orchestration=orchestration,
        production_job=job,
        controlled_production=controlled,
    )
    second = run_production_stabilization_audit(
        project_name="m7-consultant-liability",
        article_package=package,
        orchestration=orchestration,
        production_job=job,
        controlled_production=controlled,
    )
    assert first == second


def test_mismatched_production_lineage_blocks_stabilization() -> None:
    package, orchestration, job, controlled = _records()
    controlled["production_id"] = "production_fedcba9876543210"
    result = run_production_stabilization_audit(
        project_name="m7-consultant-liability",
        article_package=package,
        orchestration=orchestration,
        production_job=job,
        controlled_production=controlled,
    )
    assert result["outcome"] == "blocked"
    assert result["checks"]["controlled_production"]["status"] == "failed"


def test_incomplete_orchestration_blocks_stabilization() -> None:
    package, orchestration, job, controlled = _records()
    orchestration["lifecycle_stage"] = "running"
    result = run_production_stabilization_audit(
        project_name="m7-consultant-liability",
        article_package=package,
        orchestration=orchestration,
        production_job=job,
        controlled_production=controlled,
    )
    assert result["outcome"] == "blocked"
    assert result["checks"]["orchestration"]["status"] == "failed"


def test_invalid_job_projection_blocks_stabilization() -> None:
    package, orchestration, job, controlled = _records()
    job["current_stage"] = "qa"
    result = run_production_stabilization_audit(
        project_name="m7-consultant-liability",
        article_package=package,
        orchestration=orchestration,
        production_job=job,
        controlled_production=controlled,
    )
    assert result["outcome"] == "blocked"
    assert result["checks"]["production_job"]["status"] == "failed"


def test_invalid_delivered_wordpress_state_blocks_stabilization() -> None:
    package, orchestration, job, controlled = _records()
    controlled["delivery"]["remote_status"] = "publish"
    result = run_production_stabilization_audit(
        project_name="m7-consultant-liability",
        article_package=package,
        orchestration=orchestration,
        production_job=job,
        controlled_production=controlled,
    )
    assert result["outcome"] == "blocked"
    assert result["checks"]["controlled_production"]["status"] == "failed"


def test_publication_boundary_is_never_relaxed() -> None:
    package, orchestration, job, controlled = _records()
    controlled["publication"]["publish"] = True
    result = run_production_stabilization_audit(
        project_name="m7-consultant-liability",
        article_package=package,
        orchestration=orchestration,
        production_job=job,
        controlled_production=controlled,
    )
    assert result["outcome"] == "blocked"
    assert result["checks"]["publication_boundary"]["status"] == "failed"


def test_audit_does_not_mutate_inputs() -> None:
    package, orchestration, job, controlled = _records()
    originals = deepcopy((package, orchestration, job, controlled))
    run_production_stabilization_audit(
        project_name="m7-consultant-liability",
        article_package=package,
        orchestration=orchestration,
        production_job=job,
        controlled_production=controlled,
    )
    assert (package, orchestration, job, controlled) == originals


def test_invalid_identifier_is_rejected() -> None:
    package, orchestration, job, controlled = _records()
    job["job_id"] = "job_bad"
    with pytest.raises(ValueError, match="job_id"):
        run_production_stabilization_audit(
            project_name="m7-consultant-liability",
            article_package=package,
            orchestration=orchestration,
            production_job=job,
            controlled_production=controlled,
        )
