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
    return create_controlled_production_run(project_name="m7-consultant-liability", production_id=PRODUCTION_ID, orchestration_id=ORCHESTRATION_ID)


def _canonical_orchestration(*, lifecycle: str = "completed", delivery_mode: str = "dry_run") -> dict:
    return {
        "orchestration_id": ORCHESTRATION_ID,
        "lifecycle_stage": lifecycle,
        "lineage": {
            "report_id": "report_123",
            "decision_id": "decision_123",
            "strategy_id": "strategy_123",
            "brief_id": "brief_123",
            "draft_id": "draft_123",
            "quality_id": "quality_123",
        },
        "production": {
            "assembly": {"assembly_id": "assembly_0123456789abcdef", "lifecycle_stage": "production_assembly_ready"},
            "package": {"package_id": "package_0123456789abcdef", "lifecycle_stage": "delivery_ready", "validation_status": "validated"},
            "boundary": {"delivery_id": "delivery_0123456789abcdef", "lifecycle_stage": "delivery_ready", "delivery_status": "ready"},
            "wordpress": {"execution_mode": delivery_mode, "delivery_status": "ready" if delivery_mode == "dry_run" else "delivered", "publish": False, "human_approval_required": True},
        },
        "error": None,
    }


def test_create_run_is_deterministic_and_queued() -> None:
    first, second = _run(), _run()
    assert first == second
    assert first["status"] == "queued"
    assert first["production_checkpoints"] == {"assembly_id": None, "package_id": None, "delivery_id": None}
    assert "topic" not in first
    assert first["publication"] == {"mode": "wordpress_draft", "publish": False, "human_approval_required": True}


def test_controlled_production_does_not_accept_detached_topic() -> None:
    with pytest.raises(TypeError):
        create_controlled_production_run(project_name="m7-consultant-liability", topic="Consultant Liability Insurance", production_id=PRODUCTION_ID, orchestration_id=ORCHESTRATION_ID)


def test_primary_lifecycle_reaches_human_review() -> None:
    run = transition_controlled_production_run(_run(), status="running")
    run["production_checkpoints"] = {"assembly_id": "assembly_0123456789abcdef", "package_id": "package_0123456789abcdef", "delivery_id": "delivery_0123456789abcdef"}
    run = transition_controlled_production_run(run, status="ready_for_delivery")
    run["delivery"] = {"status": "delivered", "delivery_id": "delivery_0123456789abcdef", "post_id": 123, "edit_url": "https://example.test/wp-admin/post.php?post=123&action=edit", "remote_status": "draft", "error": None}
    run = transition_controlled_production_run(run, status="draft_delivered")
    run = transition_controlled_production_run(run, status="human_review")
    assert run["status"] == "human_review"
    assert run["human_review"]["status"] == "pending"


def test_ready_requires_canonical_checkpoints() -> None:
    run = transition_controlled_production_run(_run(), status="running")
    with pytest.raises(ValueError, match="canonical production checkpoints"):
        transition_controlled_production_run(run, status="ready_for_delivery")


def test_approved_requires_human_review() -> None:
    with pytest.raises(ValueError): transition_controlled_production_run(_run(), status="approved")


def test_rejected_requires_human_review_path() -> None:
    run = transition_controlled_production_run(_run(), status="running")
    run["production_checkpoints"] = {"assembly_id": "assembly_0123456789abcdef", "package_id": "package_0123456789abcdef", "delivery_id": "delivery_0123456789abcdef"}
    run = transition_controlled_production_run(run, status="ready_for_delivery")
    run["delivery"] = {"status": "delivered", "delivery_id": "delivery_0123456789abcdef", "post_id": 123, "edit_url": "https://example.test/wp-admin/post.php?post=123&action=edit", "remote_status": "draft", "error": None}
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
    with pytest.raises(ValueError): transition_controlled_production_run(_run(), status="human_review")


def test_invalid_identifiers_are_rejected() -> None:
    with pytest.raises(ValueError): create_controlled_production_run(project_name="project", production_id="production_bad", orchestration_id=ORCHESTRATION_ID)
    with pytest.raises(ValueError): create_controlled_production_run(project_name="project", production_id=PRODUCTION_ID, orchestration_id="orchestration_bad")


def test_run_controlled_production_dry_run_stops_before_wordpress(monkeypatch: pytest.MonkeyPatch) -> None:
    from agents.research import controlled_production
    calls = []

    def fake_orchestrator(*args, **kwargs):
        calls.append(kwargs)
        return _canonical_orchestration(delivery_mode="dry_run")

    monkeypatch.setattr(controlled_production, "run_production_orchestrator", fake_orchestrator)
    result = controlled_production.run_controlled_production("m7-consultant-liability", llm_provider=object(), deliver=False)
    assert calls[0]["deliver"] is True
    assert calls[0]["delivery_mode"] == "dry_run"
    assert result["status"] == "ready_for_delivery"
    assert result["production_id"] == "production_14f2475d9120ca35"
    assert result["orchestration_id"] == ORCHESTRATION_ID
    assert result["production_checkpoints"] == {"assembly_id": "assembly_0123456789abcdef", "package_id": "package_0123456789abcdef", "delivery_id": "delivery_0123456789abcdef"}
    assert result["delivery"]["status"] == "not_started"
    assert result["delivery"]["post_id"] is None
    assert result["publication"] == {"mode": "wordpress_draft", "publish": False, "human_approval_required": True}


def test_run_controlled_production_delivery_reaches_human_review(monkeypatch: pytest.MonkeyPatch) -> None:
    from agents.research import controlled_production
    monkeypatch.setattr(controlled_production, "run_production_orchestrator", lambda *args, **kwargs: _canonical_orchestration(delivery_mode="live"))
    result = _canonical_orchestration(delivery_mode="live")
    result["production"]["wordpress"].update({"platform_post_id": 123, "remote_status": "draft", "edit_url": "https://example.test/wp-admin/post.php?post=123&action=edit"})
    monkeypatch.setattr(controlled_production, "run_production_orchestrator", lambda *args, **kwargs: result)
    run = controlled_production.run_controlled_production("m7-consultant-liability", llm_provider=object(), deliver=True)
    assert run["status"] == "human_review"
    assert run["delivery"] == {"status": "delivered", "delivery_id": "delivery_0123456789abcdef", "post_id": 123, "edit_url": "https://example.test/wp-admin/post.php?post=123&action=edit", "remote_status": "draft", "error": None}
    assert run["human_review"] == {"required": True, "status": "pending"}
    assert run["publication"] == {"mode": "wordpress_draft", "publish": False, "human_approval_required": True}


def test_run_controlled_production_orchestration_failure_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from agents.research import controlled_production
    failed = _canonical_orchestration(lifecycle="failed")
    failed["error"] = {"stage": "article_package", "type": "PackageError", "message": "package failed"}
    monkeypatch.setattr(controlled_production, "run_production_orchestrator", lambda *args, **kwargs: failed)
    result = controlled_production.run_controlled_production("m7-consultant-liability", llm_provider=object(), deliver=False)
    assert result["status"] == "failed"
    assert result["delivery"]["status"] == "failed"
    assert result["delivery"]["error"] == {"type": "PackageError", "message": "package failed"}
    assert result["publication"]["publish"] is False


def test_run_controlled_production_delivery_failure_fails_without_publication(monkeypatch: pytest.MonkeyPatch) -> None:
    from agents.research import controlled_production
    failed = _canonical_orchestration(delivery_mode="live")
    failed["production"]["wordpress"].update({"delivery_status": "failed", "publish": False, "human_approval_required": True})
    monkeypatch.setattr(controlled_production, "run_production_orchestrator", lambda *args, **kwargs: failed)
    result = controlled_production.run_controlled_production("m7-consultant-liability", llm_provider=object(), deliver=True)
    assert result["status"] == "failed"
    assert result["delivery"]["status"] == "failed"
    assert result["delivery"]["error"]["type"] == "WordPressDeliveryFailed"
    assert result["publication"]["publish"] is False
    assert result["publication"]["mode"] == "wordpress_draft"
