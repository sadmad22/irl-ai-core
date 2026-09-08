from agents.research.production_orchestrator import STAGES, build_production_orchestration, execute_stage_plan


def _article():
    return {
        "draft_id": "draft_123",
        "brief_id": "brief_123",
        "report_id": "report_123",
        "decision_id": "decision_123",
        "strategy_id": "strategy_123",
        "lifecycle_stage": "draft_ready",
    }


def _quality():
    return {
        "quality_id": "quality_123",
        "draft_id": "draft_123",
        "brief_id": "brief_123",
        "report_id": "report_123",
        "decision_id": "decision_123",
        "strategy_id": "strategy_123",
        "lifecycle_stage": "article_draft_quality_ready",
        "outcome": "passed",
        "audit": {"validation_status": "validated"},
    }


def test_stage_order_is_locked():
    assert STAGES == (
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


def test_orchestrator_builds_package_and_completes():
    result = {
        "research_report": {"report_id": "report_123"},
        "content_brief": {"brief_id": "brief_123"},
        "article_draft": _article(),
        "article_draft_quality": _quality(),
        "editorial_review": {"outcome": "approved"},
        "seo_validation": {"outcome": "passed"},
        "claim_audit": {"outcome": "passed"},
        "publication": {"gate_status": "allowed"},
    }

    orchestration = build_production_orchestration(project_name="demo", result=result)

    assert orchestration["lifecycle_stage"] == "completed"
    assert orchestration["remaining_stages"] == []
    assert orchestration["article_package"]["lifecycle_stage"] == "production_ready"
    assert orchestration["article_package"]["lineage"]["draft_id"] == "draft_123"


def test_execute_stage_plan_stops_on_first_failure():
    calls = []

    def runner(stage, context):
        calls.append(stage)
        if stage == "structure":
            raise RuntimeError("structure failed")
        return {stage: {"status": "done"}}

    result = execute_stage_plan(project_name="demo", stage_runner=runner)

    assert result["lifecycle_stage"] == "failed"
    assert result["current_stage"] == "structure"
    assert result["completed_stages"] == ["research", "intelligence", "configuration"]
    assert result["remaining_stages"][0] == "structure"
    assert calls == ["research", "intelligence", "configuration", "structure"]


def test_execute_stage_plan_resume_requires_prior_checkpoints():
    def runner(stage, context):
        return {stage: {"status": "done"}}

    try:
        execute_stage_plan(project_name="demo", stage_runner=runner, start_stage="draft")
    except ValueError as exc:
        assert "earlier stage checkpoints" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_execute_stage_plan_resume_from_checkpoint():
    calls = []

    def runner(stage, context):
        calls.append(stage)
        return {stage: {"status": "done"}}

    result = execute_stage_plan(
        project_name="demo",
        stage_runner=runner,
        start_stage="draft",
        initial_outputs={"completed_stages": ["research", "intelligence", "configuration", "structure"]},
    )

    assert result["lifecycle_stage"] == "completed"
    assert result["completed_stages"] == list(STAGES)
    assert calls[0] == "draft"
