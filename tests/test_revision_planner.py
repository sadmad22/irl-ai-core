from agents.research.revision_planner import build_revision_plan


def _base_result():
    return {
        "article_draft": {
            "sections": [
                {"claims": [{"claim_id": "claim_2_1_abc", "evidence_refs": ["ev_1"]}]},
            ]
        },
        "article_draft_quality": {"outcome": "passed"},
        "claim_audit": {"outcome": "passed", "claims": []},
        "seo_validation": {"outcome": "passed"},
        "editorial_review": {"outcome": "approved"},
    }


def test_no_revision_is_required_for_healthy_result():
    plan = build_revision_plan(result=_base_result())
    assert plan["outcome"] == "not_required"
    assert plan["plans"] == []
    assert plan["summary"]["total"] == 0


def test_claim_audit_produces_targeted_claim_plan():
    result = _base_result()
    result["claim_audit"] = {
        "outcome": "needs_revision",
        "claims": [{
            "claim_id": "claim_2_1_abc",
            "result": "insufficient",
            "evidence_refs": ["ev_1"],
            "reason": "Assigned evidence does not provide enough lexical support for the claim.",
        }],
    }
    plan = build_revision_plan(result=result)
    item = plan["plans"][0]
    assert plan["outcome"] == "planned"
    assert item["action"] == "revise_claim"
    assert item["target"]["claim_id"] == "claim_2_1_abc"
    assert item["target"]["section_index"] == 1
    assert item["evidence_refs"] == ["ev_1"]
    assert "claim_audit" in item["rerun_gates"]


def test_quality_finding_can_target_section_and_claim():
    result = _base_result()
    result["article_draft_quality"] = {
        "outcome": "needs_revision",
        "findings": [{
            "category": "claim_evidence_grounding",
            "message": "Invalid claim evidence grounding: section_2:claim_1:grounded_without_evidence",
        }],
    }
    plan = build_revision_plan(result=result)
    item = plan["plans"][0]
    assert item["action"] == "revise_claim"
    assert item["target"]["section_index"] == 2
    assert item["target"]["claim_id"] == "claim_1"


def test_seo_failure_produces_targeted_seo_plan():
    result = _base_result()
    result["seo_validation"] = {"outcome": "needs_revision"}
    plan = build_revision_plan(result=result)
    assert plan["plans"][0]["gate"] == "seo_validation"
    assert plan["plans"][0]["action"] == "revise_seo"
    assert plan["plans"][0]["rerun_gates"] == ["seo_validation", "editorial_review", "publication"]
