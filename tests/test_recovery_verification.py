import agents.research.core_orchestrator as orchestrator
from agents.research.recovery_verification import RecoveryVerificationError, verify_recovery


def _plan(*gates):
    return {
        "recovery_id": "recovery_test",
        "strategy": "revise_claim",
        "rerun_gates": list(gates),
    }


def test_verify_recovery_passes_all_declared_gates():
    result = {
        "article_draft_quality": {"outcome": "passed"},
        "claim_audit": {"outcome": "passed"},
    }

    verification = verify_recovery(
        plan=_plan("article_draft_quality", "claim_audit"),
        result=result,
    )

    assert verification["passed"] is True
    assert verification["status"] == "passed"
    assert verification["failed_gates"] == []
    assert all(check["passed"] for check in verification["checks"])


def test_verify_recovery_fails_when_declared_gate_is_missing_or_failed():
    verification = verify_recovery(
        plan=_plan("article_draft_quality", "claim_audit"),
        result={"article_draft_quality": {"outcome": "passed"}},
    )

    assert verification["passed"] is False
    assert verification["status"] == "failed"
    assert verification["failed_gates"] == ["claim_audit"]


def test_verify_recovery_requires_declared_rerun_gates():
    try:
        verify_recovery(
            plan={"strategy": "revise_claim", "rerun_gates": []},
            result={},
        )
    except RecoveryVerificationError as exc:
        assert "no verification gates" in str(exc)
    else:
        raise AssertionError("expected RecoveryVerificationError")


def test_revision_loop_records_successful_recovery_verification(monkeypatch):
    states = iter([
        {
            "article_draft_quality": {"outcome": "passed"},
            "claim_audit": {
                "outcome": "needs_revision",
                "claims": [{
                    "claim_id": "claim_1",
                    "category": "claim_grounding",
                    "result": "disputed",
                    "evidence_refs": ["e1"],
                }],
            },
            "seo_validation": {"outcome": "passed"},
            "editorial_review": {"outcome": "approved"},
            "publication": {"gate_status": "allowed"},
            "article_draft": {"sections": [{"section_id": "s1", "claims": [{"claim_id": "claim_1", "text": "old"}]}]},
        },
        {
            "article_draft_quality": {"outcome": "passed"},
            "claim_audit": {"outcome": "passed"},
            "seo_validation": {"outcome": "passed"},
            "editorial_review": {"outcome": "approved"},
            "publication": {"gate_status": "allowed"},
            "wordpress_draft_delivery_result": {"remote_status": "draft"},
        },
    ])

    monkeypatch.setattr(orchestrator, "_load", lambda *_: {"outcome": "approved"})

    final = orchestrator.run_revision_loop(
        "test",
        pipeline_runner=lambda *args, **kwargs: next(states),
        claim_reviser=lambda project, claim_id, text, plan: {"text": "revised"},
        max_iterations=3,
    )

    history = final["revision_loop"]["history"]

    verification_entries = [
        entry["recovery_verification"]
        for entry in history
        if "recovery_verification" in entry
    ]

    assert verification_entries, "successful recovery verification was not recorded"

    verification = verification_entries[0]
    assert verification["strategy"] == "revise_claim"
    assert verification["passed"] is True
    assert verification["failed_gates"] == []
    assert final["outcome"] == "complete"
