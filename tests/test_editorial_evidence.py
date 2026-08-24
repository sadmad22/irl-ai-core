from agents.research.article_draft import build_article_draft


def _brief():
    return {
        "brief_id": "brief_editorial_001",
        "report_id": "rr_editorial_001",
        "decision_id": "dec_editorial_001",
        "strategy_id": "strat_editorial_001",
        "lifecycle_stage": "content_brief_ready",
        "content_type": "guide",
        "primary_keyword": "consultant professional liability insurance",
        "outline": [
            {"heading": "Introduction", "purpose": "introduce the topic"},
        ],
        "evidence_refs": ["ev_signal"],
        "editorial_constraints": [],
    }


def _research_only_evidence():
    return [
        {
            "evidence_id": "ev_signal",
            "domain": "authority",
            "subject": {"type": "keyword", "id": "consultant professional liability insurance"},
            "claim": {"type": "authority", "attribute": "authority_score"},
            "value": {"type": "numeric", "data": 0.85},
        }
    ]


def test_editorial_evidence_fail_safe_blocks_research_only_prose():
    draft = build_article_draft(
        content_brief=_brief(),
        evidence_records=_research_only_evidence(),
    )

    section = draft["sections"][0]
    assert draft["editorial_evidence"] == [
        {"section_index": 1, "status": "insufficient", "evidence_refs": []}
    ]
    assert section["body"] == ""
    assert section["claims"] == []


def test_editorial_evidence_keeps_publishable_evidence():
    evidence = _research_only_evidence()
    evidence.append(
        {
            "evidence_id": "ev_fact",
            "domain": "coverage",
            "subject": {"type": "keyword", "id": "consultant professional liability insurance"},
            "claim": {"type": "coverage", "attribute": "coverage"},
            "value": {"type": "categorical", "data": "professional liability"},
        }
    )
    brief = _brief()
    brief["evidence_refs"] = ["ev_signal", "ev_fact"]

    draft = build_article_draft(content_brief=brief, evidence_records=evidence)
    section = draft["sections"][0]

    assert draft["editorial_evidence"][0]["status"] == "ready"
    assert draft["editorial_evidence"][0]["evidence_refs"] == ["ev_fact"]
    assert "coverage" in section["body"]
    assert section["claims"]
    assert section["claims"][0]["grounding_status"] == "grounded"
