import agents.research.core_orchestrator as orchestrator
from agents.research.recovery_executor import RecoveryExecutionError, build_recovery_executor_registry, execute_revise_seo


def _result(*, revised=False, delivered=False):
    draft = {
        "draft_id": "draft_1",
        "title": "Accountant Insurance",
        "meta_description": "Accountant insurance guide.",
        "primary_keyword": "accountant insurance",
        "slug": "accountant-insurance",
        "sections": [{"heading": "Coverage", "body": "Coverage content."}],
    }
    result = {
        "article_draft": draft,
        "article_draft_quality": {"outcome": "passed", "findings": []},
        "claim_audit": {"outcome": "passed", "claims": []},
        "seo_validation": {
            "outcome": "passed" if revised else "needs_revision",
            "findings": [] if revised else [{"category": "seo", "target": "draft_1"}],
        },
        "editorial_review": {"outcome": "approved", "findings": []},
        "publication": {"gate_status": "allowed" if revised else "blocked"},
    }
    if delivered:
        result["wordpress_draft_delivery_result"] = {"remote_status": "draft"}
    return result


def test_revise_seo_executor_changes_only_allowed_metadata():
    result = _result()
    plan = {"strategy": "revise_seo", "target": "draft_1"}
    before_sections = result["article_draft"]["sections"][:]
    execution = execute_revise_seo(
        project_name="test",
        result=result,
        plan=plan,
        seo_reviser=lambda project, target, seo, recovery: {
            "title": "Accountant Insurance Guide",
            "meta_description": "How accountant insurance works and what coverage to consider.",
        },
    )
    assert execution["status"] == "executed"
    assert execution["target"] == "draft_1"
    assert result["article_draft"]["title"] == "Accountant Insurance Guide"
    assert result["article_draft"]["meta_description"] == "How accountant insurance works and what coverage to consider."
    assert result["article_draft"]["primary_keyword"] == "accountant insurance"
    assert result["article_draft"]["slug"] == "accountant-insurance"
    assert result["article_draft"]["sections"] == before_sections


def test_revise_seo_executor_rejects_unsupported_fields():
    result = _result()
    plan = {"strategy": "revise_seo", "target": "draft_1"}
    try:
        execute_revise_seo(
            project_name="test",
            result=result,
            plan=plan,
            seo_reviser=lambda *args: {"content": "unsafe mutation"},
        )
    except RecoveryExecutionError as exc:
        assert "unsupported fields" in str(exc)
    else:
        raise AssertionError("expected RecoveryExecutionError")


def test_revise_seo_executor_fails_closed_on_unchanged_metadata():
    result = _result()
    plan = {"strategy": "revise_seo", "target": "draft_1"}
    try:
        execute_revise_seo(
            project_name="test",
            result=result,
            plan=plan,
            seo_reviser=lambda project, target, seo, recovery: {"title": seo["title"]},
        )
    except RecoveryExecutionError as exc:
        assert "unchanged metadata" in str(exc)
    else:
        raise AssertionError("expected RecoveryExecutionError")


def test_revision_loop_executes_revise_seo_without_revision_handler(monkeypatch):
    states = iter([_result(), _result(revised=True, delivered=True)])
    calls = []
    revised = []
    monkeypatch.setattr(orchestrator, "_load", lambda *_: {"outcome": "approved"})

    def runner(*args, **kwargs):
        calls.append(1)
        return next(states)

    def seo_reviser(project, target, seo, recovery):
        revised.append((project, target, recovery["strategy"]))
        return {"title": "Accountant Insurance Guide"}

    final = orchestrator.run_revision_loop(
        "test",
        pipeline_runner=runner,
        seo_reviser=seo_reviser,
        max_iterations=2,
    )
    assert len(calls) == 2
    assert revised == [("test", "draft_1", "revise_seo")]
    assert final["outcome"] == "complete"
    assert final["revision_loop"]["status"] == "completed"
    assert final["revision_loop"]["iterations"] == 2
    assert final["revision_loop"]["revision_count"] == 1
    assert final["revision_loop"]["history"][0]["recovery_execution"]["status"] == "executed"


def test_revise_seo_executor_is_registered():
    registry = build_recovery_executor_registry(seo_reviser=lambda *args: {"title": "revised"})
    assert registry.strategies() == ("revise_seo",)
