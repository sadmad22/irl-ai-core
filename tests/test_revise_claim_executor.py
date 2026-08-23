import agents.research.core_orchestrator as orchestrator
from agents.research.recovery_executor import RecoveryExecutionError, execute_revise_claim


def _result(*, revised=False, delivered=False):
    text = "Accountants need professional liability insurance." if not revised else "Accountants may need professional liability insurance based on their services."
    claim = {"claim_id": "claim_1", "text": text, "evidence_refs": ["ev_1"]}
    result = {
        "article_draft": {
            "draft_id": "draft_1",
            "sections": [{"heading": "Coverage", "claims": [claim]}],
        },
        "article_draft_quality": {
            "outcome": "passed" if revised else "needs_revision",
            "findings": [] if revised else [{"category": "claim_grounding", "claim_id": "claim_1"}],
        },
        "claim_audit": {
            "outcome": "passed",
            "claims": [{**claim, "result": "supported"}],
        },
        "seo_validation": {"outcome": "passed"},
        "editorial_review": {"outcome": "approved"},
        "publication": {"gate_status": "allowed" if revised else "blocked"},
    }
    if delivered:
        result["wordpress_draft_delivery_result"] = {"remote_status": "draft"}
    return result


def test_revise_claim_executor_changes_targeted_claim():
    result = _result()
    plan = {"strategy": "revise_claim", "target": "claim_1"}
    execution = execute_revise_claim(
        project_name="test", result=result, plan=plan,
        claim_reviser=lambda project, claim_id, text, recovery: text.replace("need", "may need"),
    )
    assert execution["status"] == "executed"
    assert execution["target"] == "claim_1"
    assert execution["previous_text"] == "Accountants need professional liability insurance."
    assert execution["revised_text"] == "Accountants may need professional liability insurance."
    assert result["article_draft"]["sections"][0]["claims"][0]["text"] == execution["revised_text"]


def test_revise_claim_executor_fails_closed_on_empty_text():
    result = _result()
    plan = {"strategy": "revise_claim", "target": "claim_1"}
    try:
        execute_revise_claim(project_name="test", result=result, plan=plan, claim_reviser=lambda *args: "")
    except RecoveryExecutionError as exc:
        assert "empty text" in str(exc)
    else:
        raise AssertionError("expected RecoveryExecutionError")


def test_revise_claim_executor_fails_closed_on_unchanged_text():
    result = _result()
    plan = {"strategy": "revise_claim", "target": "claim_1"}
    try:
        execute_revise_claim(project_name="test", result=result, plan=plan, claim_reviser=lambda project, claim_id, text, recovery: text)
    except RecoveryExecutionError as exc:
        assert "unchanged text" in str(exc)
    else:
        raise AssertionError("expected RecoveryExecutionError")


def test_revision_loop_executes_revise_claim_without_revision_handler(monkeypatch):
    states = iter([_result(), _result(revised=True, delivered=True)])
    calls = []
    revised = []
    monkeypatch.setattr(orchestrator, "_load", lambda *_: {"outcome": "approved"})

    def runner(*args, **kwargs):
        calls.append(1)
        return next(states)

    def claim_reviser(project, claim_id, text, recovery):
        revised.append((project, claim_id, text, recovery["strategy"]))
        return text.replace("need", "may need")

    final = orchestrator.run_revision_loop("test", pipeline_runner=runner, claim_reviser=claim_reviser, max_iterations=2)
    assert len(calls) == 2
    assert revised == [("test", "claim_1", "Accountants need professional liability insurance.", "revise_claim")]
    assert final["outcome"] == "complete"
    assert final["revision_loop"]["status"] == "completed"
    assert final["revision_loop"]["iterations"] == 2
    assert final["revision_loop"]["revision_count"] == 1
    assert final["revision_loop"]["history"][0]["recovery_execution"]["status"] == "executed"


def test_revise_claim_executor_is_registered():
    from agents.research.recovery_executor import build_recovery_executor_registry
    registry = build_recovery_executor_registry(claim_reviser=lambda *args: "revised")
    assert registry.strategies() == ("revise_claim",)
