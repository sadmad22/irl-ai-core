import pytest

from agents.research.content_optimization import build_content_optimization


def base():
    return {
        "article": {"title": "Consultant Insurance", "content": "Consultant insurance covers professional liability and errors and omissions.", "word_count": 9, "headings": ["Professional Liability", "Cost"]},
        "outline_editor": {
            "brief_id": "brief-1", "report_id": "report-1", "decision_id": "decision-1", "strategy_id": "strategy-1", "config_id": "config-1", "outline_editor_id": "outline-1", "lifecycle_stage": "outline_editor_ready",
            "sections": [{"heading": "Professional Liability", "required": True}, {"heading": "Claims Made Policy", "required": True}],
        },
        "semantic_seo": {
            "semantic_id": "sem-1", "brief_id": "brief-1", "report_id": "report-1", "decision_id": "decision-1", "strategy_id": "strategy-1", "lifecycle_stage": "semantic_seo_ready",
            "secondary_keywords": ["consultant insurance"], "semantic_keywords": ["defense costs"], "entities": ["errors and omissions"], "questions": ["What does consultant insurance cover?"],
        },
        "details_to_include": {"lifecycle_stage": "details_to_include_ready", "details_to_include": ["coverage limits"]},
    }


def test_detects_missing_content_and_recommendations():
    x = base()
    result = build_content_optimization(**x)
    assert result["lifecycle_stage"] == "content_optimization_ready"
    assert any(g["target"] == "Claims Made Policy" for g in result["gaps"])
    assert any(r["type"] == "add_section" for r in result["recommendations"])


def test_detects_semantic_gap():
    result = build_content_optimization(**base())
    gap = next(g for g in result["gaps"] if g["target"] == "defense costs")
    assert gap["category"] == "semantic"


def test_threshold_filters_covered_targets():
    x = base()
    x["article"]["content"] += " Defense costs coverage limits."
    result = build_content_optimization(**x, threshold=0.5)
    assert not any(g["target"] == "defense costs" for g in result["gaps"])


def test_same_input_is_deterministic():
    x = base()
    assert build_content_optimization(**x) == build_content_optimization(**x)


def test_reordered_semantic_lists_keep_identity():
    a = base()
    b = base()
    b["semantic_seo"]["semantic_keywords"] = list(reversed(b["semantic_seo"]["semantic_keywords"]))
    b["semantic_seo"]["questions"] = list(reversed(b["semantic_seo"]["questions"]))
    assert build_content_optimization(**a)["content_optimization_id"] == build_content_optimization(**b)["content_optimization_id"]


def test_competitive_mode_requires_verified_dataforseo():
    with pytest.raises(ValueError, match="DataForSEO"):
        build_content_optimization(**base(), analysis_mode="competitive")


def test_competitive_mode_uses_only_dataforseo_targets():
    x = base()
    x["dataforseo"] = {"source": "dataforseo", "verified": True, "competitor_topics": ["consultant cyber insurance"]}
    result = build_content_optimization(**x, analysis_mode="competitive")
    assert {g["target"] for g in result["gaps"]} == {"consultant cyber insurance"}


def test_combined_mode_includes_dataforseo_and_core_targets():
    x = base()
    x["dataforseo"] = {"source": "dataforseo", "verified": True, "competitor_topics": ["consultant cyber insurance"]}
    result = build_content_optimization(**x, analysis_mode="combined")
    assert any(g["source"] == "dataforseo" for g in result["gaps"])
    assert any(g["source"] == "outline_editor" for g in result["gaps"])


@pytest.mark.parametrize("field", ["brief_id", "report_id", "decision_id", "strategy_id"])
def test_missing_lineage_is_rejected(field):
    x = base()
    del x["outline_editor"][field]
    with pytest.raises(ValueError):
        build_content_optimization(**x)


def test_invalid_upstream_lifecycle_is_rejected():
    x = base()
    x["outline_editor"]["lifecycle_stage"] = "draft"
    with pytest.raises(ValueError, match="outline_editor_ready"):
        build_content_optimization(**x)


def test_invalid_semantic_lifecycle_is_rejected():
    x = base()
    x["semantic_seo"]["lifecycle_stage"] = "draft"
    with pytest.raises(ValueError, match="semantic_seo_ready"):
        build_content_optimization(**x)


def test_invalid_threshold_is_rejected():
    with pytest.raises(ValueError, match="threshold"):
        build_content_optimization(**base(), threshold=1.1)


def test_unknown_analysis_mode_is_rejected():
    with pytest.raises(ValueError, match="analysis_mode"):
        build_content_optimization(**base(), analysis_mode="foo")


def test_unverified_dataforseo_is_rejected():
    x = base()
    x["dataforseo"] = {"source": "dataforseo", "verified": False, "competitor_topics": ["cyber insurance"]}
    with pytest.raises(ValueError, match="verified"):
        build_content_optimization(**x, analysis_mode="combined")


def test_summary_matches_gaps():
    result = build_content_optimization(**base())
    assert result["summary"]["gap_count"] == len(result["gaps"])
    assert result["summary"]["high_priority_count"] == sum(g["severity"] == "high" for g in result["gaps"])


def test_gap_order_is_deterministic():
    x = base()
    result = build_content_optimization(**x)
    keys = [({"high": 0, "medium": 1, "low": 2}[g["severity"]], g["category"], g["target"].casefold()) for g in result["gaps"]]
    assert keys == sorted(keys)
