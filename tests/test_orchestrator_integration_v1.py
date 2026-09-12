from __future__ import annotations

from agents.research.production_orchestrator import STAGES, execute_stage_plan


CANONICAL_STAGES = (
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
    "production_assembly",
    "article_package",
    "production_delivery_boundary",
    "wordpress_delivery",
)


LINEAGE = {
    "report_id": "report_123",
    "decision_id": "decision_123",
    "strategy_id": "strategy_123",
    "brief_id": "brief_123",
    "draft_id": "draft_123",
    "quality_id": "quality_123",
}


PRODUCTION_INTENT = {
    "target": "wordpress",
    "mode": "wordpress_draft",
    "publish": False,
    "human_approval_required": True,
}


def test_orchestrator_uses_canonical_fourteen_stage_order():
    assert STAGES == CANONICAL_STAGES


def test_stage_plan_returns_canonical_production_checkpoints():
    def runner(stage, context):
        return {stage: {"status": "done"}}

    result = execute_stage_plan(project_name="demo", stage_runner=runner)

    assert result["completed_stages"] == list(CANONICAL_STAGES)
    assert result["remaining_stages"] == []
    assert result["current_stage"] is None
    assert result["error"] is None
    assert "production" in result
    assert set(result["production"]) == {"assembly", "package", "boundary", "wordpress"}
    assert "article_package" not in result


def test_controlled_wordpress_completion_resolves_to_human_review():
    def runner(stage, context):
        return {stage: {"status": "done"}}

    result = execute_stage_plan(project_name="demo", stage_runner=runner)

    result["lineage"] = dict(LINEAGE)
    result["production"] = {
        "assembly": {
            "assembly_id": "assembly_0123456789abcdef",
            "lifecycle_stage": "production_assembly_ready",
        },
        "package": {
            "package_id": "package_0123456789abcdef",
            "lifecycle_stage": "delivery_ready",
            "validation_status": "validated",
        },
        "boundary": {
            "delivery_id": "delivery_0123456789abcdef",
            "lifecycle_stage": "human_review",
            "delivery_status": "delivered",
        },
        "wordpress": {
            "execution_mode": "live",
            "delivery_status": "delivered",
            "remote_status": "draft",
            "publish": False,
            "human_approval_required": True,
        },
    }
    result["production"]["wordpress"]["production_intent"] = PRODUCTION_INTENT

    assert result["lifecycle_stage"] == "human_review"
    assert result["remaining_stages"] == []
    assert result["current_stage"] is None
    assert result["production"]["wordpress"]["publish"] is False
    assert result["production"]["wordpress"]["human_approval_required"] is True


def test_fail_stop_keeps_first_failed_stage_and_does_not_continue():
    calls = []

    def runner(stage, context):
        calls.append(stage)
        if stage == "production_assembly":
            raise RuntimeError("assembly failed")
        return {stage: {"status": "done"}}

    result = execute_stage_plan(project_name="demo", stage_runner=runner)

    assert result["lifecycle_stage"] == "failed"
    assert result["current_stage"] == "production_assembly"
    assert result["completed_stages"] == list(CANONICAL_STAGES[:10])
    assert result["remaining_stages"][0] == "production_assembly"
    assert calls == list(CANONICAL_STAGES[:10]) + ["production_assembly"]


def test_resume_requires_all_prior_canonical_checkpoints():
    def runner(stage, context):
        return {stage: {"status": "done"}}

    try:
        execute_stage_plan(
            project_name="demo",
            stage_runner=runner,
            start_stage="article_package",
            initial_outputs={"completed_stages": list(CANONICAL_STAGES[:10])},
        )
    except ValueError as exc:
        assert "earlier stage checkpoints" in str(exc)
    else:
        raise AssertionError("expected ValueError")
