import agents.research.core_orchestrator as orchestrator
from agents.research.editorial_execution_contract import validate_editorial_revision
from agents.research.recovery_executor import RecoveryExecutionError, build_recovery_executor_registry, execute_revise_editorial


def _result(*, revised=False, delivered=False):
    result = {
        "article_draft": {
            "draft_id": "draft_1",
            "title": "Editorial Test",
            "sections": [{"section_id": "coverage", "heading": "Coverage", "body": "Clear coverage content."}],
            "evidence_refs": ["ev-1"],
        },
        "article_draft_quality": {"outcome": "passed", "findings": []},
        "claim_audit": {"outcome": "passed", "claims": []},
        "seo_validation": {"outcome": "passed", "findings": []},
        "editorial_review": {"outcome": "approved" if revised else "needs_revision", "findings": [] if revised else [{"category": "editorial", "target": "draft_1"}]},
        "publication": {"gate_status": "allowed"},
    }
    if delivered:
        result["wordpress_draft_delivery_result"] = {"remote_status": "draft"}
    return result


def test_editorial_contract_accepts_only_section_id_and_content():
    assert validate_editorial_revision({"section_id": "coverage", "content": "Revised."}) == {"section_id": "coverage", "content": "Revised."}


def test_revise_editorial_changes_one_section_only():
    result = _result()
    before = dict(result["article_draft"]["sections"][0])
    execution = execute_revise_editorial(
        project_name="test",
        result=result,
        plan={"strategy": "revise_editorial", "target": "draft_1", "failure_type": "editorial"},
        editorial_reviser=lambda project, target, failure_type, snapshot: {"section_id": "coverage", "content": "More precise coverage content."},
    )
    assert execution["status"] == "executed"
    assert result["article_draft"]["sections"][0]["heading"] == before["heading"]
    assert result["article_draft"]["sections"][0]["body"] == "More precise coverage content."
    assert result["article_draft"]["evidence_refs"] == ["ev-1"]


def test_revise_editorial_rejects_unsupported_mutation_fields():
    try:
        execute_revise_editorial(
            project_name="test",
            result=_result(),
            plan={"strategy": "revise_editorial", "target": "draft_1", "failure_type": "editorial"},
            editorial_reviser=lambda *args: {"section_id": "coverage", "content": "Revised.", "evidence_refs": ["unsafe"]},
        )
    except RecoveryExecutionError as exc:
        assert "unsupported fields" in str(exc)
    else:
        raise AssertionError("expected RecoveryExecutionError")


def test_revise_editorial_rejects_unchanged_content():
    try:
        execute_revise_editorial(
            project_name="test",
            result=_result(),
            plan={"strategy": "revise_editorial", "target": "draft_1", "failure_type": "editorial"},
            editorial_reviser=lambda *args: {"section_id": "coverage", "content": "Clear coverage content."},
        )
    except RecoveryExecutionError as exc:
        assert "unchanged content" in str(exc)
    else:
        raise AssertionError("expected RecoveryExecutionError")


def test_revise_editorial_registers_in_execution_contract():
    registry = build_recovery_executor_registry(editorial_reviser=lambda *args: {"section_id": "coverage", "content": "Revised."})
    assert registry.strategies() == ("revise_editorial",)


def test_revision_loop_executes_revise_editorial_without_revision_handler(monkeypatch):
    calls = {"reviser": 0, "runs": 0}

    def runner(*args, **kwargs):
        calls["runs"] += 1
        return _result(revised=calls["runs"] >= 2, delivered=calls["runs"] >= 2)

    def reviser(*args):
        calls["reviser"] += 1
        return {"section_id": "coverage", "content": "Editorially revised coverage content."}

    monkeypatch.setattr(orchestrator, "_load", lambda project, name: {"outcome": "approved"})
    outcome = orchestrator.run_revision_loop(
        "test",
        pipeline_runner=runner,
        editorial_reviser=reviser,
        revision_handler=None,
        max_iterations=3,
    )
    assert outcome["next_action"] == "complete"
    assert calls["reviser"] == 1
    assert calls["runs"] == 2
