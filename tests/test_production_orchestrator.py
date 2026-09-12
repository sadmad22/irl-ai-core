from agents.research import production_orchestrator as orchestrator
from agents.research.production_orchestrator import STAGES, PRODUCTION_INTENT, build_production_orchestration, execute_stage_plan


def _article():
    return {"draft_id": "draft_123", "brief_id": "brief_123", "report_id": "report_123", "decision_id": "decision_123", "strategy_id": "strategy_123", "lifecycle_stage": "draft_ready"}


def _quality():
    return {"quality_id": "quality_123", "draft_id": "draft_123", "brief_id": "brief_123", "report_id": "report_123", "decision_id": "decision_123", "strategy_id": "strategy_123", "lifecycle_stage": "article_draft_quality_ready", "outcome": "passed", "audit": {"validation_status": "validated"}}


def test_stage_order_is_locked():
    assert STAGES == ("research", "intelligence", "configuration", "structure", "draft", "editorial_cleanup", "media", "linking", "optimization", "qa", "production_assembly", "article_package", "production_delivery_boundary", "wordpress_delivery")


def test_non_delivery_orchestration_completes_selected_qa_mode():
    result = {"research_report": {"report_id": "report_123"}, "content_brief": {"brief_id": "brief_123"}, "article_draft": _article(), "article_draft_quality": _quality(), "editorial_review": {"outcome": "approved"}, "seo_validation": {"outcome": "passed"}, "claim_audit": {"outcome": "passed"}, "publication": {"gate_status": "allowed"}}
    orchestration = build_production_orchestration(project_name="demo", result=result)
    assert orchestration["lifecycle_stage"] == "completed"
    assert orchestration["current_stage"] is None
    assert orchestration["remaining_stages"] == []
    assert orchestration["completed_stages"] == ["research", "intelligence", "configuration", "structure", "draft", "editorial_cleanup", "optimization", "qa"]
    assert "article_package" not in orchestration


def test_canonical_production_intent_is_immutable():
    result = {"production_intent": {"target": "other", "mode": "publish", "publish": True, "human_approval_required": False}}
    canonical = orchestrator._canonical_artifacts(result)
    assert canonical["production_intent"] == PRODUCTION_INTENT
    assert canonical["production_intent"] is not result["production_intent"]


def test_legacy_article_production_contract_is_not_used():
    assert not hasattr(orchestrator, "build_article_production")
    result = build_production_orchestration(project_name="demo", result={})
    assert result["lifecycle_stage"] == "running"
    assert result["current_stage"] == "research"


def test_execute_stage_plan_stops_on_first_failure():
    calls = []
    def runner(stage, context):
        calls.append(stage)
        if stage == "structure": raise RuntimeError("structure failed")
        return {stage: {"status": "done"}}
    result = execute_stage_plan(project_name="demo", stage_runner=runner)
    assert result["lifecycle_stage"] == "failed"
    assert result["current_stage"] == "structure"
    assert result["completed_stages"] == list(STAGES[:3])
    assert result["remaining_stages"][0] == "structure"
    assert calls == list(STAGES[:3]) + ["structure"]


def test_execute_stage_plan_resume_requires_prior_checkpoints():
    def runner(stage, context): return {stage: {"status": "done"}}
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
    result = execute_stage_plan(project_name="demo", stage_runner=runner, start_stage="draft", initial_outputs={"completed_stages": list(STAGES[:4])})
    assert result["lifecycle_stage"] == "completed"
    assert result["completed_stages"] == list(STAGES)
    assert calls[0] == "draft"
