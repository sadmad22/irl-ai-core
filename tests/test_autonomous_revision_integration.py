from agents.research.core_orchestrator import run_revision_loop


def test_autonomous_revision_plan_drives_real_revision_loop():
    calls = []
    state = {"revised": False}

    def controlled_runner(
        project_name,
        *,
        deliver,
        connection,
        transport,
    ):
        calls.append("runner")

        base_draft = {
            "draft_id": "draft_controlled",
            "sections": [
                {
                    "heading": "Controlled Section",
                    "claims": [
                        {
                            "claim_id": "claim_1_1_abc",
                            "evidence_refs": ["ev_1"],
                        }
                    ],
                }
            ],
        }

        if not state["revised"]:
            return {
                "article_draft": base_draft,
                "article_draft_quality": {
                    "outcome": "passed",
                    "findings": [],
                },
                "claim_audit": {
                    "outcome": "needs_revision",
                    "claims": [
                        {
                            "claim_id": "claim_1_1_abc",
                            "result": "insufficient",
                            "evidence_refs": ["ev_1"],
                            "reason": "Controlled integration failure",
                        }
                    ],
                },
                "seo_validation": {
                    "outcome": "passed",
                },
                "editorial_review": {
                    "outcome": "approved",
                },
                "publication": {
                    "gate_status": "blocked",
                },
            }

        return {
            "article_draft": base_draft,
            "article_draft_quality": {
                "outcome": "passed",
                "findings": [],
            },
            "claim_audit": {
                "outcome": "passed",
                "claims": [
                    {
                        "claim_id": "claim_1_1_abc",
                        "result": "supported",
                        "evidence_refs": ["ev_1"],
                    }
                ],
            },
            "seo_validation": {
                "outcome": "passed",
            },
            "editorial_review": {
                "outcome": "approved",
            },
            "publication": {
                "gate_status": "allowed",
            },
            "wordpress_draft_delivery_result": {
                "remote_status": "draft",
                "post_id": 9999,
            },
        }

    def controlled_revision_handler(
        project_name,
        action,
        result,
        orchestration,
        iteration,
    ):
        plan = orchestration["revision_plan"]
        recovery = orchestration["adaptive_recovery"]

        assert plan["outcome"] == "planned"
        assert plan["summary"]["total"] == 1

        item = plan["plans"][0]
        recovery_item = recovery["plans"][0]

        assert item["gate"] == "claim_audit"
        assert item["action"] == "revise_claim"
        assert item["target"]["claim_id"] == "claim_1_1_abc"
        assert item["target"]["section_index"] == 1

        assert recovery["outcome"] == "planned"
        assert recovery["summary"]["total"] == 1
        assert recovery_item["strategy"] == "acquire_evidence"
        assert recovery_item["target"] == "claim_1_1_abc"
        assert recovery_item["rerun_gates"] == ["claim_audit"]

        calls.append(
            (
                "revision",
                action,
                recovery_item["strategy"],
                item["target"]["section_index"],
                item["target"]["claim_id"],
            )
        )

        state["revised"] = True

    result = run_revision_loop(
        "expat-health-insurance",
        deliver=False,
        pipeline_runner=controlled_runner,
        revision_handler=controlled_revision_handler,
        max_iterations=2,
    )

    assert result["outcome"] == "complete"
    assert result["next_action"] == "complete"
    assert result["iterations"] == 1
    assert result["revision_loop"]["revision_count"] == 1
    assert result["revision_loop"]["status"] == "completed"

    assert calls == [
        "runner",
        ("revision", "acquire_evidence", "acquire_evidence", 1, "claim_1_1_abc"),
        "runner",
    ]
