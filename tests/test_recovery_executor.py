import agents.research.core_orchestrator as orchestrator
from agents.research.recovery_executor import RecoveryExecutionError, execute_acquire_evidence


def _result(*, repaired=False, delivered=False):
    evidence_refs = ["ev_2"] if repaired else ["ev_1"]
    claim = {"claim_id": "claim_1", "evidence_refs": evidence_refs}
    result = {
        "article_draft": {
            "draft_id": "draft_1",
            "sections": [{"heading": "Coverage", "claims": [claim]}],
        },
        "article_draft_quality": {"outcome": "passed", "findings": []},
        "claim_audit": {
            "outcome": "passed" if repaired else "needs_revision",
            "claims": [{**claim, "result": "supported" if repaired else "insufficient"}],
        },
        "seo_validation": {"outcome": "passed"},
        "editorial_review": {"outcome": "approved"},
        "publication": {"gate_status": "allowed" if repaired else "blocked"},
    }
    if delivered:
        result["wordpress_draft_delivery_result"] = {"remote_status": "draft"}
    return result


def test_acquire_evidence_executor_attaches_new_refs():
    result = _result()
    plan = {"strategy": "acquire_evidence", "target": "claim_1"}

    execution = execute_acquire_evidence(
        project_name="test",
        result=result,
        plan=plan,
        evidence_acquirer=lambda project, claim_id, refs, recovery: ["ev_2"],
    )

    assert execution["status"] == "executed"
    assert execution["acquired_evidence_refs"] == ["ev_2"]
    assert result["article_draft"]["sections"][0]["claims"][0]["evidence_refs"] == ["ev_1", "ev_2"]


def test_acquire_evidence_executor_fails_closed_without_new_refs():
    result = _result()
    plan = {"strategy": "acquire_evidence", "target": "claim_1"}

    try:
        execute_acquire_evidence(
            project_name="test",
            result=result,
            plan=plan,
            evidence_acquirer=lambda project, claim_id, refs, recovery: refs,
        )
    except RecoveryExecutionError as exc:
        assert "no new evidence" in str(exc)
    else:
        raise AssertionError("expected RecoveryExecutionError")


def test_revision_loop_executes_acquire_evidence_without_revision_handler(monkeypatch):
    states = iter([_result(), _result(repaired=True, delivered=True)])
    calls = []
    acquired = []

    monkeypatch.setattr(orchestrator, "_load", lambda *_: {"outcome": "approved"})

    def runner(*args, **kwargs):
        calls.append(1)
        return next(states)

    def evidence_acquirer(project, claim_id, refs, recovery):
        acquired.append((project, claim_id, refs, recovery["strategy"]))
        return ["ev_2"]

    final = orchestrator.run_revision_loop(
        "test",
        pipeline_runner=runner,
        evidence_acquirer=evidence_acquirer,
        max_iterations=2,
    )

    assert len(calls) == 2
    assert acquired == [("test", "claim_1", ["ev_1"], "acquire_evidence")]
    assert final["outcome"] == "complete"
    assert final["revision_loop"]["status"] == "completed"
    assert final["revision_loop"]["iterations"] == 2
    assert final["revision_loop"]["revision_count"] == 1
    assert final["revision_loop"]["history"][0]["recovery_execution"]["status"] == "executed"


def test_revision_loop_stops_when_evidence_executor_fails(monkeypatch):
    monkeypatch.setattr(orchestrator, "_load", lambda *_: {"outcome": "approved"})

    final = orchestrator.run_revision_loop(
        "test",
        pipeline_runner=lambda *args, **kwargs: _result(),
        evidence_acquirer=lambda *args: [],
        max_iterations=2,
    )

    assert final["outcome"] == "action_required"
    assert final["next_action"] == "acquire_evidence"
    assert final["revision_loop"]["status"] == "stopped"
    assert final["revision_loop"]["history"][0]["recovery_execution"]["status"] == "failed"
