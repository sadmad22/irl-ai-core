import agents.research.core_orchestrator as orchestrator
from agents.research.recovery_executor import (
    RecoveryExecutionContext,
    RecoveryExecutionError,
    RecoveryExecutorRegistry,
    SectionRecoveryExecutor,
    execute_recovery,
)


def _result(*, revised=False, delivered=False):
    section = {
        "section_id": "coverage",
        "heading": "Coverage",
        "content": "Original coverage guidance." if not revised else "Revised coverage guidance.",
        "evidence_refs": ["ev_1"],
        "claims": [{"claim_id": "claim_1", "text": "Coverage claim."}],
    }
    result = {
        "article_draft": {"draft_id": "draft_1", "sections": [section]},
        "article_draft_quality": {
            "outcome": "passed" if revised else "needs_revision",
            "findings": [] if revised else [{"category": "section_grounding", "target": "coverage", "evidence_refs": ["ev_1"]}],
        },
        "claim_audit": {"outcome": "passed", "claims": [{**section["claims"][0], "result": "supported"}]},
        "seo_validation": {"outcome": "passed"},
        "editorial_review": {"outcome": "approved"},
        "publication": {"gate_status": "allowed" if revised else "blocked"},
    }
    if delivered:
        result["wordpress_draft_delivery_result"] = {"remote_status": "draft"}
    return result


def _plan(target="coverage"):
    return {"strategy": "revise_section", "target": target}


def test_revise_section_executor_changes_only_targeted_section():
    result = _result()
    result["article_draft"]["sections"].append({"section_id": "cost", "title": "Cost", "content": "Original cost content.", "evidence_refs": ["e2"]})
    execution = execute_recovery(
        project_name="test", result=result, plan=_plan(),
        section_reviser=lambda project, target, text, recovery: "Revised coverage guidance.",
    )
    assert execution["status"] == "executed"
    assert execution["target"] == "coverage"
    assert result["article_draft"]["sections"][0]["content"] == "Revised coverage guidance."
    assert result["article_draft"]["sections"][1]["content"] == "Original cost content."


def test_revise_section_executor_preserves_metadata():
    result = _result()
    execute_recovery(
        project_name="test", result=result, plan=_plan(),
        section_reviser=lambda *args: "Updated.",
    )
    section = result["article_draft"]["sections"][0]
    assert section["section_id"] == "coverage"
    assert section["heading"] == "Coverage"
    assert section["evidence_refs"] == ["ev_1"]
    assert section["claims"] == [{"claim_id": "claim_1", "text": "Coverage claim."}]


def test_revise_section_executor_resolves_heading_target():
    result = _result()
    execute_recovery(
        project_name="test", result=result, plan=_plan("Coverage"),
        section_reviser=lambda *args: "Updated.",
    )
    assert result["article_draft"]["sections"][0]["content"] == "Updated."


def test_revise_section_executor_fails_closed_on_missing_target():
    try:
        execute_recovery(project_name="test", result=_result(), plan=_plan("missing"), section_reviser=lambda *args: "Updated.")
    except RecoveryExecutionError as exc:
        assert "section target not found" in str(exc)
    else:
        raise AssertionError("expected RecoveryExecutionError")


def test_revise_section_executor_fails_closed_on_empty_content():
    try:
        execute_recovery(project_name="test", result=_result(), plan=_plan(), section_reviser=lambda *args: "")
    except RecoveryExecutionError as exc:
        assert "empty content" in str(exc)
    else:
        raise AssertionError("expected RecoveryExecutionError")


def test_revise_section_executor_fails_closed_on_unchanged_content():
    try:
        execute_recovery(project_name="test", result=_result(), plan=_plan(), section_reviser=lambda project, target, text, recovery: text)
    except RecoveryExecutionError as exc:
        assert "unchanged content" in str(exc)
    else:
        raise AssertionError("expected RecoveryExecutionError")


def test_revision_loop_executes_revise_section_without_revision_handler(monkeypatch):
    states = iter([_result(), _result(revised=True, delivered=True)])
    calls = []
    revised = []
    monkeypatch.setattr(orchestrator, "_load", lambda *_: {"outcome": "approved"})

    def runner(*args, **kwargs):
        calls.append(1)
        return next(states)

    def section_reviser(project, target, text, recovery):
        revised.append((project, target, text, recovery["strategy"]))
        return "Revised coverage guidance."

    final = orchestrator.run_revision_loop("test", pipeline_runner=runner, section_reviser=section_reviser, max_iterations=2)
    assert len(calls) == 2
    assert revised == [("test", "coverage", "Original coverage guidance.", "revise_section")]
    assert final["outcome"] == "complete"
    assert final["revision_loop"]["status"] == "completed"
    assert final["revision_loop"]["iterations"] == 2
    assert final["revision_loop"]["history"][0]["recovery_execution"]["strategy"] == "revise_section"


def test_revise_section_executor_uses_unified_context():
    result = _result()
    context = RecoveryExecutionContext(project_name="test", result=result, plan=_plan())
    executor = SectionRecoveryExecutor(lambda *args: "Updated.")
    execution = executor.execute(context)
    assert execution["status"] == "executed"
    assert result["article_draft"]["sections"][0]["content"] == "Updated."


def test_revise_section_executor_is_registered():
    registry = RecoveryExecutorRegistry([SectionRecoveryExecutor(lambda *args: "revised")])
    assert registry.strategies() == ("revise_section",)
    assert isinstance(registry.get("revise_section"), SectionRecoveryExecutor)
