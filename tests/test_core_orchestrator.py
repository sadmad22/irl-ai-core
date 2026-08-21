from agents.research.core_orchestrator import build_orchestration_result


def _result(**overrides):
    result = {
        "article_draft_quality": {"outcome": "passed"},
        "claim_audit": {"outcome": "passed"},
        "seo_validation": {"outcome": "passed"},
        "editorial_review": {"outcome": "approved"},
        "publication": {"gate_status": "allowed"},
    }
    result.update(overrides)
    return result


def _decision(outcome="approved"):
    return {"outcome": outcome}


def test_completed_pipeline_is_orchestrated_as_complete():
    orchestration = build_orchestration_result(
        project_name="expat-health-insurance",
        result={**_result(), "wordpress_draft_delivery_result": {"remote_status": "draft"}},
        decision=_decision(),
    )

    assert orchestration["lifecycle_stage"] == "completed"
    assert orchestration["current_stage"] == "complete"
    assert orchestration["next_action"] == "complete"
    assert orchestration["gates"]["claim_audit"] == "passed"
    assert orchestration["gates"]["publication"] == "allowed"


def test_quality_failure_routes_to_article_revision():
    orchestration = build_orchestration_result(
        project_name="test",
        result=_result(article_draft_quality={"outcome": "needs_revision"}),
        decision=_decision(),
    )

    assert orchestration["lifecycle_stage"] == "action_required"
    assert orchestration["next_action"] == "revise_article_draft"


def test_claim_audit_failure_routes_to_claim_revision():
    orchestration = build_orchestration_result(
        project_name="test",
        result=_result(claim_audit={"outcome": "needs_revision"}),
        decision=_decision(),
    )

    assert orchestration["next_action"] == "revise_claims"


def test_editorial_failure_routes_to_editorial_revision():
    orchestration = build_orchestration_result(
        project_name="test",
        result=_result(editorial_review={"outcome": "needs_revision"}),
        decision=_decision(),
    )

    assert orchestration["next_action"] == "revise_editorial"


def test_unapproved_decision_stops_orchestration_before_quality_gates():
    orchestration = build_orchestration_result(
        project_name="test",
        result=_result(),
        decision=_decision("deferred"),
    )

    assert orchestration["lifecycle_stage"] == "blocked"
    assert orchestration["next_action"] == "stop"
    assert orchestration["decision_outcome"] == "deferred"


def test_approved_pipeline_without_delivery_routes_to_wordpress_delivery():
    orchestration = build_orchestration_result(
        project_name="test",
        result=_result(),
        decision=_decision(),
    )

    assert orchestration["next_action"] == "deliver_wordpress_draft"
