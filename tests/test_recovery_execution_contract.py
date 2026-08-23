import pytest

from agents.research.recovery_executor import (
    EvidenceRecoveryExecutor,
    RecoveryExecutionContext,
    RecoveryExecutionError,
    RecoveryExecutorRegistry,
    build_recovery_executor_registry,
    execute_recovery,
)


def _result():
    return {
        "article_draft": {
            "sections": [
                {"heading": "Coverage", "claims": [{"claim_id": "claim_1", "evidence_refs": ["ev_1"]}]}
            ]
        }
    }


def test_registry_registers_and_resolves_by_strategy():
    acquirer = lambda project, claim_id, refs, plan: ["ev_2"]
    registry = build_recovery_executor_registry(evidence_acquirer=acquirer)

    assert registry.strategies() == ("acquire_evidence",)
    assert isinstance(registry.get("acquire_evidence"), EvidenceRecoveryExecutor)


def test_registry_rejects_duplicate_strategy():
    acquirer = lambda project, claim_id, refs, plan: ["ev_2"]
    executor = EvidenceRecoveryExecutor(acquirer)
    registry = RecoveryExecutorRegistry([executor])

    with pytest.raises(ValueError, match="already registered"):
        registry.register(executor)


def test_registry_fails_closed_for_unknown_strategy():
    registry = RecoveryExecutorRegistry()

    with pytest.raises(RecoveryExecutionError, match="no executor is registered"):
        registry.get("revise_claim")


def test_contract_context_is_shared_by_executor():
    result = _result()
    seen = []

    class RecordingExecutor:
        strategy = "record"

        def execute(self, context):
            seen.append(context)
            return {"strategy": self.strategy, "status": "executed", "changed": False}

    registry = RecoveryExecutorRegistry([RecordingExecutor()])
    plan = {"strategy": "record", "target": "claim_1"}

    execution = execute_recovery(
        project_name="test",
        result=result,
        plan=plan,
        registry=registry,
    )

    assert execution == {"strategy": "record", "status": "executed", "changed": False}
    assert len(seen) == 1
    assert isinstance(seen[0], RecoveryExecutionContext)
    assert seen[0].project_name == "test"
    assert seen[0].result is result
    assert seen[0].plan == plan


def test_execute_recovery_uses_registry_executor():
    result = _result()
    registry = build_recovery_executor_registry(
        evidence_acquirer=lambda project, claim_id, refs, plan: ["ev_2"]
    )

    execution = execute_recovery(
        project_name="test",
        result=result,
        plan={"strategy": "acquire_evidence", "target": "claim_1"},
        registry=registry,
    )

    assert execution["status"] == "executed"
    assert execution["changed"] is True
    assert result["article_draft"]["sections"][0]["claims"][0]["evidence_refs"] == ["ev_1", "ev_2"]


def test_empty_default_registry_requires_executor_configuration():
    registry = build_recovery_executor_registry()

    with pytest.raises(RecoveryExecutionError, match="no executor is registered"):
        execute_recovery(
            project_name="test",
            result=_result(),
            plan={"strategy": "acquire_evidence", "target": "claim_1"},
            registry=registry,
        )
