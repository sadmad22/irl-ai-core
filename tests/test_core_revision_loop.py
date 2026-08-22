import agents.research.core_orchestrator as orchestrator


def _result(*, quality="passed", claim_audit="passed", seo="passed", editorial="approved", publication="allowed", delivered=False):
    result = {
        "article_draft_quality": {"outcome": quality},
        "claim_audit": {"outcome": claim_audit},
        "seo_validation": {"outcome": seo},
        "editorial_review": {"outcome": editorial},
        "publication": {"gate_status": publication},
    }
    if delivered:
        result["wordpress_draft_delivery_result"] = {"remote_status": "draft"}
    return result


def test_revision_loop_retries_after_article_revision(monkeypatch):
    states = iter([
        _result(quality="needs_revision"),
        _result(delivered=True),
    ])
    calls = []

    monkeypatch.setattr(orchestrator, "_load", lambda *_: {"outcome": "approved"})

    def runner(*args, **kwargs):
        calls.append(kwargs)
        return next(states)

    def revise(project, action, result, orchestration, iteration):
        assert project == "test"
        assert action == "revise_article_draft"
        assert iteration == 1
        assert orchestration["adaptive_recovery"]["outcome"] == "not_required"

    final = orchestrator.run_revision_loop(
        "test",
        pipeline_runner=runner,
        revision_handler=revise,
        max_iterations=3,
    )

    assert final["outcome"] == "complete"
    assert final["next_action"] == "complete"
    assert final["revision_loop"]["status"] == "completed"
    assert final["revision_loop"]["iterations"] == 2
    assert [item["action"] for item in final["revision_loop"]["history"]] == [
        "revise_article_draft",
        "complete",
    ]
    assert len(calls) == 2


def test_revision_loop_routes_claim_failure_to_adaptive_recovery(monkeypatch):
    states = iter([_result(claim_audit="needs_revision"), _result(delivered=True)])
    actions = []

    monkeypatch.setattr(orchestrator, "_load", lambda *_: {"outcome": "approved"})

    def runner(*args, **kwargs):
        result = next(states)
        if result["claim_audit"]["outcome"] != "passed":
            result["claim_audit"]["claims"] = [{
                "claim_id": "claim_1",
                "result": "insufficient",
                "evidence_refs": ["e1"],
            }]
        return result

    def revise(project, action, result, orchestration, iteration):
        actions.append((action, iteration, orchestration["adaptive_recovery"]["plans"][0]["strategy"]))

    final = orchestrator.run_revision_loop(
        "test",
        pipeline_runner=runner,
        revision_handler=revise,
    )

    assert actions == [("acquire_evidence", 1, "acquire_evidence")]
    assert final["outcome"] == "complete"


def test_revision_loop_fails_closed_on_unrecoverable_structured_failure(monkeypatch):
    monkeypatch.setattr(orchestrator, "_load", lambda *_: {"outcome": "approved"})

    final = orchestrator.run_revision_loop(
        "test",
        pipeline_runner=lambda *args, **kwargs: {
            **_result(quality="passed", claim_audit="needs_revision"),
            "claim_audit": {
                "outcome": "needs_revision",
                "claims": [{"claim_id": "claim_1", "result": "unsupported"}],
            },
        },
        revision_handler=lambda *args: (_ for _ in ()).throw(AssertionError("handler must not run")),
    )

    assert final["outcome"] == "blocked"
    assert final["next_action"] == "stop"
    assert final["adaptive_recovery"]["outcome"] == "stopped"
    assert final["revision_loop"]["status"] == "stopped"


def test_revision_loop_fails_closed_without_handler(monkeypatch):
    monkeypatch.setattr(orchestrator, "_load", lambda *_: {"outcome": "approved"})

    final = orchestrator.run_revision_loop(
        "test",
        pipeline_runner=lambda *args, **kwargs: _result(seo="needs_revision"),
    )

    assert final["outcome"] == "action_required"
    assert final["next_action"] == "revise_seo"
    assert final["adaptive_recovery"]["outcome"] == "not_required"
    assert final["revision_loop"]["status"] == "handler_required"
    assert final["revision_loop"]["iterations"] == 1


def test_revision_loop_stops_at_bounded_limit(monkeypatch):
    monkeypatch.setattr(orchestrator, "_load", lambda *_: {"outcome": "approved"})
    calls = []

    def runner(*args, **kwargs):
        calls.append(1)
        return _result(editorial="needs_revision")

    final = orchestrator.run_revision_loop(
        "test",
        pipeline_runner=runner,
        revision_handler=lambda *args: None,
        max_iterations=2,
    )

    assert final["outcome"] == "action_required"
    assert final["next_action"] == "revise_editorial"
    assert final["adaptive_recovery"]["outcome"] == "not_required"
    assert final["revision_loop"]["status"] == "revision_limit_reached"
    assert final["revision_loop"]["iterations"] == 2
    assert len(calls) == 2
