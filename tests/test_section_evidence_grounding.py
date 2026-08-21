from agents.research.section_evidence_grounding import ground_evidence_by_section


def _outline():
    return [
        {"heading": "Introduction", "purpose": "introduce the topic"},
        {"heading": "Costs and Pricing Factors", "purpose": "explain pricing factors"},
        {"heading": "Frequently Asked Questions", "purpose": "answer common questions"},
    ]


def _records():
    return [
        {
            "evidence_id": "ev_cost",
            "domain": "business",
            "claim": {"type": "business_value", "attribute": "pricing"},
            "value": {"type": "categorical", "data": "commercial"},
            "subject": {"type": "keyword", "id": "expat health insurance"},
            "source": {"artifact": "search-metrics.json"},
        },
        {
            "evidence_id": "ev_question",
            "domain": "question",
            "claim": {"type": "question", "attribute": "faq"},
            "value": {"type": "boolean", "data": True},
            "subject": {"type": "keyword", "id": "expat health insurance"},
            "source": {"artifact": "question-analysis.json"},
        },
        {
            "evidence_id": "ev_entity",
            "domain": "entity",
            "claim": {"type": "entity_presence", "attribute": "mentioned"},
            "value": {"type": "boolean", "data": True},
            "subject": {"type": "entity", "id": "example.org"},
            "source": {"artifact": "serp-analysis.json"},
        },
    ]


def test_grounding_prefers_section_relevant_evidence():
    result = ground_evidence_by_section(
        outline=_outline(),
        evidence_refs=["ev_cost", "ev_question", "ev_entity"],
        evidence_records=_records(),
        per_section=1,
    )

    assert result == [["ev_entity"], ["ev_cost"], ["ev_question"]]


def test_grounding_is_deterministic_and_stays_within_lineage():
    kwargs = {
        "outline": _outline(),
        "evidence_refs": ["ev_cost", "ev_question", "ev_entity"],
        "evidence_records": _records(),
        "per_section": 2,
    }
    first = ground_evidence_by_section(**kwargs)
    second = ground_evidence_by_section(**kwargs)

    assert first == second
    assert all(ref in kwargs["evidence_refs"] for refs in first for ref in refs)
    assert all(refs for refs in first)
