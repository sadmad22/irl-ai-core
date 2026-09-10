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


def _completed_orchestration() -> dict:
    return {
        "orchestration_id": ORCHESTRATION_ID,
        "lifecycle_stage": "completed",
        "article_package": {"production_id": PRODUCTION_ID},
    }


def test_run_controlled_production_without_delivery_reaches_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    from agents.research import controlled_production

    monkeypatch.setattr(
        controlled_production,
        "run_production_orchestrator",
        lambda *args, **kwargs: _completed_orchestration(),
    )

    result = controlled_production.run_controlled_production(
        "m7-consultant-liability",
        topic="Consultant Liability Insurance",
        deliver=False,
    )

    assert result["status"] == "ready_for_delivery"
    assert result["production_id"] == PRODUCTION_ID
    assert result["orchestration_id"] == ORCHESTRATION_ID
    assert result["publication"]["publish"] is False


def test_run_controlled_production_delivery_reaches_human_review(monkeypatch: pytest.MonkeyPatch) -> None:
    from agents.research import controlled_production

    monkeypatch.setattr(
        controlled_production,
        "run_production_orchestrator",
        lambda *args, **kwargs: _completed_orchestration(),
    )
    monkeypatch.setattr(
        controlled_production,
        "deliver_wordpress_draft_from_production",
        lambda *args, **kwargs: {
            "connector_id": "wpconn_0123456789abcdef",
            "response": {
                "delivery_status": "delivered",
                "post_id": 123,
                "edit_url": "https://example.test/wp-admin/post.php?post=123&action=edit",
                "remote_status": "draft",
                "error": None,
            },
        },
    )

    result = controlled_production.run_controlled_production(
        "m7-consultant-liability",
        topic="Consultant Liability Insurance",
        deliver=True,
    )

    assert result["status"] == "human_review"
    assert result["delivery"] == {
        "status": "delivered",
        "delivery_id": "wpconn_0123456789abcdef",
        "post_id": 123,
        "edit_url": "https://example.test/wp-admin/post.php?post=123&action=edit",
        "remote_status": "draft",
        "error": None,
    }
    assert result["human_review"] == {"required": True, "status": "pending"}
    assert result["publication"] == {
        "mode": "wordpress_draft",
        "publish": False,
        "human_approval_required": True,
    }


def test_run_controlled_production_incomplete_orchestration_fails_with_lineage(monkeypatch: pytest.MonkeyPatch) -> None:
    from agents.research import controlled_production

    incomplete = _completed_orchestration()
    incomplete["lifecycle_stage"] = "running"
    monkeypatch.setattr(
        controlled_production,
        "run_production_orchestrator",
        lambda *args, **kwargs: incomplete,
    )

    result = controlled_production.run_controlled_production(
        "m7-consultant-liability",
        topic="Consultant Liability Insurance",
        deliver=False,
    )

    assert result["status"] == "failed"
    assert result["production_id"] == PRODUCTION_ID
    assert result["orchestration_id"] == ORCHESTRATION_ID
    assert result["delivery"]["status"] == "failed"
    assert result["delivery"]["error"]["type"] == "ProductionOrchestrationIncomplete"


def test_run_controlled_production_delivery_failure_fails_without_publication(monkeypatch: pytest.MonkeyPatch) -> None:
    from agents.research import controlled_production

    monkeypatch.setattr(
        controlled_production,
        "run_production_orchestrator",
        lambda *args, **kwargs: _completed_orchestration(),
    )
    monkeypatch.setattr(
        controlled_production,
        "deliver_wordpress_draft_from_production",
        lambda *args, **kwargs: {
            "connector_id": "wpconn_0123456789abcdef",
            "response": {"delivery_status": "failed"},
        },
    )

    result = controlled_production.run_controlled_production(
        "m7-consultant-liability",
        topic="Consultant Liability Insurance",
        deliver=True,
    )

    assert result["status"] == "failed"
    assert result["delivery"]["status"] == "failed"
    assert result["delivery"]["error"]["type"] == "WordPressDeliveryFailed"
    assert result["publication"]["publish"] is False
    assert result["publication"]["mode"] == "wordpress_draft"
