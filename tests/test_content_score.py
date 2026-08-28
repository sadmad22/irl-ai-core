from agents.research.content_score import build_content_score


def _inputs():
    report = {
        "report_id": "r1",
        "keyword": "consultant insurance cost",
        "search_intent": {"primary_intent": "Informational"},
    }
    strategy = {
        "strategy_id": "s1",
        "primary_keyword": "consultant insurance cost",
        "sections": ["Introduction", "Coverage and Key Factors", "Costs and Pricing Factors"],
        "entities": ["Insureon", "Progressive"],
        "questions": [
            "How much does consultant insurance cost?",
            {"text": "What coverage do consultants need?"},
        ],
    }
    brief = {"brief_id": "b1", "evidence_refs": ["e1", "e2"]}
    draft = {
        "draft_id": "d1",
        "title": "Consultant Insurance Cost: Coverage and Pricing Guide",
        "sections": [
            {"heading": "Introduction", "body": "This guide explains consultant insurance cost and how consultants evaluate coverage."},
            {"heading": "Coverage and Key Factors", "body": "Insureon and Progressive are examples used in the research. Consultants need to compare coverage."},
            {"heading": "Costs and Pricing Factors", "body": "Consultant insurance cost depends on coverage needs and business risk. How much does consultant insurance cost? What coverage do consultants need?"},
        ],
        "evidence_refs": ["e1", "e2"],
    }
    return report, strategy, brief, draft


def test_content_score_schema_and_total():
    report, strategy, brief, draft = _inputs()
    result = build_content_score(
        research_report=report,
        content_strategy=strategy,
        content_brief=brief,
        article_draft=draft,
        serp_results=[{"title": "Consultant Insurance Costs", "domain": "example.com"}],
    )
    assert result["lifecycle_stage"] == "content_score_ready"
    assert result["method_version"] == "v1.1"
    assert 0 <= result["score"] <= 100
    assert result["grade"] in {"A", "B", "C", "D", "F"}
    assert sum(v["score"] for v in result["components"].values()) == result["score"]
    assert result["audit"]["validation_status"] == "validated"


def test_content_score_preserves_question_objects():
    report, strategy, brief, draft = _inputs()
    result = build_content_score(research_report=report, content_strategy=strategy, content_brief=brief, article_draft=draft)
    assert not any("Uncovered questions" in gap for gap in result["gaps"])


def test_content_score_is_deterministic():
    report, strategy, brief, draft = _inputs()
    first = build_content_score(research_report=report, content_strategy=strategy, content_brief=brief, article_draft=draft)
    second = build_content_score(research_report=report, content_strategy=strategy, content_brief=brief, article_draft=draft)
    assert first == second


def test_content_score_does_not_require_serp_api_data():
    report, strategy, brief, draft = _inputs()
    result = build_content_score(research_report=report, content_strategy=strategy, content_brief=brief, article_draft=draft, serp_results=[])
    assert result["components"]["serp_benchmark"]["score"] == 5.0


def test_content_score_requires_lineage_ids():
    report, strategy, brief, draft = _inputs()
    draft["draft_id"] = ""
    try:
        build_content_score(research_report=report, content_strategy=strategy, content_brief=brief, article_draft=draft)
    except ValueError as exc:
        assert "IDs are required" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_v11_semantic_heading_matching_avoids_exact_string_dependency():
    report, strategy, brief, draft = _inputs()
    strategy["sections"] = ["Costs and Pricing Factors"]
    draft["sections"] = [{"heading": "Costs, Pricing & Key Factors", "body": "Consultant insurance cost depends on business risk and coverage."}]
    result = build_content_score(research_report=report, content_strategy=strategy, content_brief=brief, article_draft=draft)
    assert result["components"]["topic_coverage"]["score"] == 15.0
    assert result["components"]["heading_structure"]["score"] == 10.0


def test_v11_question_matching_accepts_supported_partial_answers():
    report, strategy, brief, draft = _inputs()
    strategy["questions"] = [{"text": "What coverage do independent consultants need for professional liability?"}]
    draft["sections"][-1]["body"] = "Independent consultants should consider professional liability coverage based on their services, contracts, and risk exposure."
    result = build_content_score(research_report=report, content_strategy=strategy, content_brief=brief, article_draft=draft)
    assert result["components"]["question_coverage"]["score"] == 10.0
    assert not any("Uncovered questions" in gap for gap in result["gaps"])


def test_v11_readability_accounts_for_long_sentences_and_paragraphs():
    report, strategy, brief, draft = _inputs()
    draft["sections"] = [{"heading": "Introduction", "body": "Short sentences improve clarity. " * 8}]
    result = build_content_score(research_report=report, content_strategy=strategy, content_brief=brief, article_draft=draft)
    assert result["components"]["readability_quality"]["score"] >= 4.0
