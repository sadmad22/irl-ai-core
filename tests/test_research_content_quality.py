from agents.research.article_draft import build_article_draft


def _brief():
    return {
        "brief_id": "brief-1",
        "report_id": "report-1",
        "decision_id": "decision-1",
        "strategy_id": "strategy-1",
        "lifecycle_stage": "content_brief_ready",
        "primary_keyword": "consultant professional liability insurance",
        "content_type": "guide",
        "evidence_refs": ["e-authority", "e-coverage"],
        "outline": [{"heading": "Introduction", "purpose": "Introduce the topic."}],
        "editorial_constraints": [],
    }


def test_research_only_signals_are_not_serialized_as_article_prose():
    draft = build_article_draft(
        content_brief=_brief(),
        evidence_records=[
            {
                "evidence_id": "e-authority",
                "domain": "authority",
                "claim": {"attribute": "authority_score"},
                "value": {"data": 0.8556},
                "subject": {"id": "consultant professional liability insurance"},
            },
            {
                "evidence_id": "e-coverage",
                "domain": "insurance",
                "claim": {"attribute": "coverage"},
                "value": {"data": "professional liability"},
                "subject": {"id": "consultant professional liability insurance"},
            },
        ],
    )

    body = draft["sections"][0]["body"]
    assert "authority score" not in body
    assert "0.8556" not in body
    assert "coverage" in body
    assert draft["sections"][0]["claims"][0]["grounding_status"] == "grounded"
