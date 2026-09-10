from __future__ import annotations

import pytest

from agents.research.controlled_production import (
    create_controlled_production_run,
    mark_controlled_production_failed,
    transition_controlled_production_run,
)


PRODUCTION_ID = "production_0123456789abcdef"
ORCHESTRATION_ID = "orchestration_0123456789abcdef"


def _run() -> dict:
    return create_controlled_production_run(
        project_name="m7-consultant-liability",
        topic="Consultant Liability Insurance",
        production_id=PRODUCTION_ID,
        orchestration_id=ORCHESTRATION_ID,
    )


def test_create_run_is_deterministic_and_queued() -> None:
    first = _run()
    second = _run()
    assert first == second
    assert first["status"] == "queued"
    assert first["publication"] == {
        "mode": "wordpress_draft",
        "publish": False,
        "human_approval_required": True,
    }


def test_primary_lifecycle_reaches_human_review() -> None:
    run = transition_controlled_production_run(_run(), status="running")
    run = transition_controlled_production_run(run, status="ready_for_delivery")
    run["delivery"] = {
        "status": "delivered",
        "delivery_id": "wpconn_0123456789abcdef",
        "post_id": 123,
        "edit_url": "https://example.test/wp-admin/post.php?post=123&action=edit",
        "remote_status": "draft",
        "error": None,
    }
    run = transition_controlled_production_run(run, status="draft_delivered")
    run = transition_controlled_production_run(run, status="human_review")
    assert run["status"] == "human_review"
    assert run["human_review"]["status"] == "pending"


def test_approved_requires_human_review() -> None:
    run = _run()
    with pytest.raises(ValueError):
        transition_controlled_production_run(run, status="approved")


def test_rejected_requires_human_review_path() -> None:
    run = transition_controlled_production_run(_run(), status="running")
    run = transition_controlled_production_run(run, status="ready_for_delivery")
    run["delivery"] = {
        "status": "delivered",
        "delivery_id": "wpconn_0123456789abcdef",
        "post_id": 123,
        "edit_url": "https://example.test/wp-admin/post.php?post=123&action=edit",
        "remote_status": "draft",
        "error": None,
    }
    run = transition_controlled_production_run(run, status="draft_delivered")
    run = transition_controlled_production_run(run, status="human_review")
    run = transition_controlled_production_run(run, status="rejected")
    assert run["status"] == "rejected"
    assert run["human_review"]["status"] == "rejected"


def test_failed_run_preserves_lineage_and_records_error() -> None:
    run = mark_controlled_production_failed(_run(), error_type="TestError", message="controlled failure")
    assert run["status"] == "failed"
    assert run["production_id"] == PRODUCTION_ID
    assert run["orchestration_id"] == ORCHESTRATION_ID
    assert run["delivery"]["error"] == {"type": "TestError", "message": "controlled failure"}


def test_invalid_transition_is_rejected() -> None:
    with pytest.raises(ValueError):
        transition_controlled_production_run(_run(), status="human_review")


def test_invalid_identifiers_are_rejected() -> None:
    with pytest.raises(ValueError):
        create_controlled_production_run(
            project_name="project",
            topic="topic",
            production_id="production_bad",
            orchestration_id=ORCHESTRATION_ID,
        )
    with pytest.raises(ValueError):
        create_controlled_production_run(
            project_name="project",
            topic="topic",
            production_id=PRODUCTION_ID,
            orchestration_id="orchestration_bad",
        )
