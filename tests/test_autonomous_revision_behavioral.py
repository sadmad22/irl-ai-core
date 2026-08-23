from agents.research.core_orchestrator import run_revision_loop


def test_autonomous_revision_loop_changes_failed_artifact_and_reaches_completion():
    """Behavioral test: a failed claim is actually repaired between pipeline runs."""
    state = {
        "evidence_refs": ["ev_1"],
        "runner_count": 0,
        "revision_count": 0,
    }

    def controlled_runner(
        project_name,
        *,
        deliver,
        connection,
        transport,
    ):
        state["runner_count"] += 1

        claim = {
            "claim_id": "claim_1_1_abc",
            "evidence_refs": list(state["evidence_refs"]),
        }
        repaired = state["revision_count"] == 1 and state["evidence_refs"] == ["ev_2"]

        return {
            "article_draft": {
                "draft_id": "draft_behavioral",
                "sections": [
                    {
                        "heading": "Controlled Section",
                        "claims": [claim],
                    }
                ],
            },
            "article_draft_quality": {"outcome": "passed", "findings": []},
            "claim_audit": {
                "outcome": "passed" if repaired else "needs_revision",
                "claims": [
                    {
                        **claim,
                        "result": "supported" if repaired else "insufficient",
                        "reason": "Evidence is insufficient" if not repaired else "Evidence supports claim",
                    }
                ],
            },
            "seo_validation": {"outcome": "passed"},
            "editorial_review": {"outcome": "approved"},
            "publication": {"gate_status": "allowed" if repaired else "blocked"},
            **(
                {"wordpress_draft_delivery_result": {"remote_status": "draft", "post_id": 1001}}
                if repaired
                else {}
            ),
        }

    def revision_handler(project_name, action, result, orchestration, iteration):
        assert project_name == "expat-health-insurance"
        assert iteration == 1
        assert action == "acquire_evidence"
        assert orchestration["next_action"] == "acquire_evidence"
        assert orchestration["revision_plan"]["plans"][0]["action"] == "revise_claim"
        assert orchestration["revision_plan"]["plans"][0]["target"]["claim_id"] == "claim_1_1_abc"
        assert orchestration["adaptive_recovery"]["plans"][0]["strategy"] == "acquire_evidence"

        # This is the behavioral hinge: the handler changes the artifact state
        # that the next pipeline run will consume.
        state["evidence_refs"] = ["ev_2"]
        state["revision_count"] += 1

    result = run_revision_loop(
        "expat-health-insurance",
        deliver=False,
        pipeline_runner=controlled_runner,
        revision_handler=revision_handler,
        max_iterations=2,
    )

    assert state["runner_count"] == 2
    assert state["revision_count"] == 1
    assert result["outcome"] == "complete"
    assert result["next_action"] == "complete"
    assert result["revision_loop"]["status"] == "completed"
    assert result["revision_loop"]["iterations"] == 2
    assert result["revision_loop"]["revision_count"] == 1

    history = result["revision_loop"]["history"]
    assert history[0]["action"] == "acquire_evidence"
    assert history[0]["outcome"] == "action_required"
    assert history[1]["action"] == "complete"
    assert history[1]["outcome"] == "complete"
