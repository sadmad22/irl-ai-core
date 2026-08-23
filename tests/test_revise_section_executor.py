from agents.research.recovery_executor import (
    RecoveryExecutionContext,
    RecoveryExecutionError,
    RecoveryExecutorRegistry,
    SectionRecoveryExecutor,
    execute_recovery,
)


def _result():
    return {
        "article_draft": {
            "sections": [
                {
                    "section_id": "coverage",
                    "title": "Coverage",
                    "content": "Original coverage content.",
                    "evidence_refs": ["e1"],
                    "claims": [{"claim_id": "claim_1", "text": "A claim."}],
                },
                {
                    "section_id": "cost",
                    "title": "Cost",
                    "content": "Original cost content.",
                    "evidence_refs": ["e2"],
                },
            ]
        }
    }


def _plan(target="coverage"):
    return {"strategy": "revise_section", "target": target}


def test_revise_section_mutates_only_targeted_section():
    result = _result()
    execution = execute_recovery(
        project_name="expat-health-insurance",
        result=result,
        plan=_plan(),
        section_reviser=lambda project, target, text, plan: text + " Revised.",
    )

    assert execution["strategy"] == "revise_section"
    assert execution["status"] == "executed"
    assert result["article_draft"]["sections"][0]["content"] == "Original coverage content. Revised."
    assert result["article_draft"]["sections"][1]["content"] == "Original cost content."


def test_revise_section_preserves_section_metadata():
    result = _result()
    before = dict(result["article_draft"]["sections"][0])
    execute_recovery(
        project_name="project",
        result=result,
        plan=_plan(),
        section_reviser=lambda project, target, text, plan: "Revised section.",
    )
    section = result["article_draft"]["sections"][0]
    assert section["section_id"] == before["section_id"]
    assert section["title"] == before["title"]
    assert section["evidence_refs"] == before["evidence_refs"]
    assert section["claims"] == before["claims"]


def test_revise_section_resolves_title_target():
    result = _result()
    execute_recovery(
        project_name="project",
        result=result,
        plan=_plan("Coverage"),
        section_reviser=lambda project, target, text, plan: "Updated.",
    )
    assert result["article_draft"]["sections"][0]["content"] == "Updated."


def test_revise_section_rejects_missing_target():
    result = _result()
    try:
        execute_recovery(
            project_name="project",
            result=result,
            plan=_plan("missing"),
            section_reviser=lambda project, target, text, plan: "Updated.",
        )
    except RecoveryExecutionError as exc:
        assert "section target not found" in str(exc)
    else:
        raise AssertionError("expected RecoveryExecutionError")


def test_revise_section_rejects_empty_revision():
    result = _result()
    try:
        execute_recovery(
            project_name="project",
            result=result,
            plan=_plan(),
            section_reviser=lambda project, target, text, plan: "   ",
        )
    except RecoveryExecutionError as exc:
        assert "empty content" in str(exc)
    else:
        raise AssertionError("expected RecoveryExecutionError")


def test_revise_section_rejects_unchanged_revision():
    result = _result()
    try:
        execute_recovery(
            project_name="project",
            result=result,
            plan=_plan(),
            section_reviser=lambda project, target, text, plan: text,
        )
    except RecoveryExecutionError as exc:
        assert "unchanged content" in str(exc)
    else:
        raise AssertionError("expected RecoveryExecutionError")


def test_registry_registers_revise_section_executor():
    registry = RecoveryExecutorRegistry(
        [SectionRecoveryExecutor(lambda project, target, text, plan: "Updated.")]
    )
    assert registry.strategies() == ("revise_section",)
    assert isinstance(registry.get("revise_section"), SectionRecoveryExecutor)


def test_context_executes_revise_section_without_revision_handler():
    result = _result()
    context = RecoveryExecutionContext(
        project_name="project",
        result=result,
        plan=_plan(),
    )
    executor = SectionRecoveryExecutor(lambda project, target, text, plan: "Autonomous revision.")
    execution = executor.execute(context)
    assert execution["status"] == "executed"
    assert result["article_draft"]["sections"][0]["content"] == "Autonomous revision."
