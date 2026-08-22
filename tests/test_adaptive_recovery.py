from agents.research.adaptive_recovery import plan_recoveries, plan_recovery


def claim_audit(result="insufficient", claim_id="claim_1", refs=None):
    return {"outcome": "needs_revision", "claims": [{"claim_id": claim_id, "result": result, "evidence_refs": refs or []}]}


def test_insufficient_claim_evidence_acquires_evidence():
    plan = plan_recovery(gate="claim_audit", result=claim_audit())
    assert plan["strategy"] == "acquire_evidence"
    assert plan["target"] == "claim_1"


def test_disputed_claim_acquires_evidence():
    plan = plan_recovery(gate="claim_audit", result=claim_audit("disputed", refs=["e1"]))
    assert plan["strategy"] == "acquire_evidence"
    assert plan["failure_type"] == "disputed_claim"


def test_claim_grounding_failure_revises_claim():
    result = {"outcome": "needs_revision", "findings": [{"category": "claim_evidence_grounding", "claim_id": "claim_2"}]}
    plan = plan_recovery(gate="article_draft_quality", result=result)
    assert plan["strategy"] == "revise_claim"
    assert plan["target"] == "claim_2"


def test_section_grounding_failure_revises_section():
    result = {"outcome": "needs_revision", "findings": [{"category": "section_evidence_grounding", "target": "Coverage"}]}
    plan = plan_recovery(gate="article_draft_quality", result=result)
    assert plan["strategy"] == "revise_section"
    assert plan["target"] == "Coverage"


def test_seo_failure_revises_seo():
    result = {"outcome": "needs_revision", "draft_id": "draft_1", "findings": [{"category": "title"}]}
    assert plan_recovery(gate="seo_validation", result=result)["strategy"] == "revise_seo"


def test_editorial_failure_revises_editorial():
    result = {"outcome": "needs_revision", "draft_id": "draft_1", "findings": [{"category": "unsupported_claims"}]}
    assert plan_recovery(gate="editorial_review", result=result)["strategy"] == "revise_editorial"


def test_missing_claim_id_stops():
    plan = plan_recovery(gate="article_draft_quality", result={"outcome": "needs_revision", "findings": [{"category": "claim_grounding"}]})
    assert plan["strategy"] == "stop"
    assert plan["status"] == "stopped"


def test_unknown_gate_stops():
    plan = plan_recovery(gate="unknown", result={"outcome": "needs_revision"})
    assert plan["strategy"] == "stop"
    assert plan["failure_type"] == "unknown_gate"


def test_healthy_result_requires_no_recovery():
    assert plan_recovery(gate="seo_validation", result={"outcome": "passed"}) is None


def test_multiple_failures_are_deterministic_and_ordered():
    results = {
        "editorial_review": {"outcome": "needs_revision", "draft_id": "draft", "findings": [{"category": "editorial"}]},
        "claim_audit": {"outcome": "needs_revision", "claims": [
            {"claim_id": "b", "result": "disputed"},
            {"claim_id": "a", "result": "insufficient"},
        ]},
    }
    first = plan_recoveries(results=results)
    second = plan_recoveries(results=results)
    assert first == second
    assert [plan["target"] for plan in first] == ["a", "b", "draft"]
    assert [plan["recovery_id"] for plan in first] == [plan["recovery_id"] for plan in second]
