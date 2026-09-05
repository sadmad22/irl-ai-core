import copy

import pytest

from agents.research.ai_content_cleaning import build_ai_content_cleaning


LINEAGE = {
    "draft_id": "draft_1",
    "brief_id": "brief_1",
    "report_id": "report_1",
    "decision_id": "decision_1",
    "strategy_id": "strategy_1",
}


def draft(**overrides):
    data = {
        **LINEAGE,
        "lifecycle_stage": "draft_ready",
        "sections": [
            {"heading": "Introduction", "body": "This policy covers common professional risks. The wording should remain clear."},
            {"heading": "Coverage", "body": "Review the limits carefully. Avoid unnecessary repetition."},
        ],
    }
    data.update(overrides)
    return data


class Provider:
    def __init__(self, result=None):
        self.result = result or {
            "status": "cleaned",
            "sections": [
                {"section_index": 0, "cleaned_body": "This policy covers common professional risks. The wording should remain clear."},
                {"section_index": 1, "cleaned_body": "Review the limits carefully and avoid unnecessary repetition."},
            ],
            "changes": [{"section_index": 1, "category": "clarity", "description": "Combined redundant wording."}],
            "risk_flags": [],
        }
        self.calls = []

    def clean(self, *, sections, editorial_rules):
        self.calls.append((sections, editorial_rules))
        return self.result


def test_builds_ready_contract():
    result = build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider())
    assert result["lifecycle_stage"] == "editorial_cleanup_ready"
    assert result["status"] == "cleaned"
    assert result["editorial_cleanup_id"].startswith("editorial_cleanup_")


def test_preserves_lineage():
    result = build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider())
    for field, value in LINEAGE.items():
        assert result[field] == value


def test_preserves_headings_and_original_bodies():
    source = draft()
    result = build_ai_content_cleaning(article_draft=source, llm_provider=Provider())
    assert result["cleaned_sections"][0]["heading"] == "Introduction"
    assert result["cleaned_sections"][0]["original_body"] == source["sections"][0]["body"]


def test_provider_receives_deep_copies():
    provider = Provider()
    source = draft()
    build_ai_content_cleaning(article_draft=source, llm_provider=provider)
    sections, rules = provider.calls[0]
    assert sections is not source["sections"]
    assert rules["preserve_claims"] is True
    sections[0]["body"] = "mutated"
    assert source["sections"][0]["body"] != "mutated"


def test_accepts_tone_and_point_of_view_configuration():
    provider = Provider()
    result = build_ai_content_cleaning(
        article_draft=draft(),
        llm_provider=provider,
        tone_of_voice={"tone_of_voice_id": "tone_1", "lifecycle_stage": "tone_of_voice_ready"},
        point_of_view={"point_of_view_id": "pov_1", "lifecycle_stage": "point_of_view_ready"},
    )
    assert result["lifecycle_stage"] == "editorial_cleanup_ready"
    rules = provider.calls[0][1]
    assert rules["tone_of_voice_id"] == "tone_1"
    assert rules["point_of_view_id"] == "pov_1"


def test_requires_provider():
    with pytest.raises(ValueError, match="requires an explicitly injected LLM provider"):
        build_ai_content_cleaning(article_draft=draft(), llm_provider=None)


def test_requires_draft_ready():
    with pytest.raises(ValueError, match="draft_ready"):
        build_ai_content_cleaning(article_draft=draft(lifecycle_stage="drafting"), llm_provider=Provider())


def test_requires_complete_lineage():
    broken = draft()
    del broken["strategy_id"]
    with pytest.raises(ValueError, match="strategy_id"):
        build_ai_content_cleaning(article_draft=broken, llm_provider=Provider())


def test_rejects_empty_sections():
    with pytest.raises(ValueError, match="non-empty"):
        build_ai_content_cleaning(article_draft=draft(sections=[]), llm_provider=Provider())


def test_rejects_empty_section_body():
    with pytest.raises(ValueError, match="heading and body"):
        build_ai_content_cleaning(article_draft=draft(sections=[{"heading": "A", "body": ""}]), llm_provider=Provider())


def test_rejects_provider_without_clean():
    with pytest.raises(ValueError, match="must expose clean"):
        build_ai_content_cleaning(article_draft=draft(), llm_provider=object())


def test_rejects_non_object_provider_result():
    provider = Provider(result=[])
    with pytest.raises(ValueError, match="return an object"):
        build_ai_content_cleaning(article_draft=draft(), llm_provider=provider)


def test_rejects_unknown_provider_fields():
    result = Provider().result | {"extra": True}
    with pytest.raises(ValueError, match="unsupported fields"):
        build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider(result=result))


def test_rejects_invalid_provider_status():
    result = Provider().result | {"status": "published"}
    with pytest.raises(ValueError, match="status"):
        build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider(result=result))


def test_rejects_section_count_mismatch():
    result = Provider().result | {"sections": Provider().result["sections"][:1]}
    with pytest.raises(ValueError, match="exactly one section"):
        build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider(result=result))


def test_rejects_duplicate_or_missing_section_indexes():
    sections = [
        {"section_index": 0, "cleaned_body": "One."},
        {"section_index": 0, "cleaned_body": "Two."},
    ]
    result = Provider().result | {"sections": sections}
    with pytest.raises(ValueError, match="section indexes"):
        build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider(result=result))


def test_risk_flags_force_needs_review():
    result = Provider().result | {"status": "cleaned", "risk_flags": ["meaning_change"]}
    output = build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider(result=result))
    assert output["status"] == "needs_review"
    assert output["risk_flags"] == ["meaning_change"]


def test_rejects_unsupported_risk_flag():
    result = Provider().result | {"risk_flags": ["hallucination"]}
    with pytest.raises(ValueError, match="risk_flags"):
        build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider(result=result))


def test_rejects_invalid_change_category():
    result = Provider().result | {"changes": [{"section_index": 0, "category": "seo", "description": "Changed wording."}]}
    with pytest.raises(ValueError, match="category"):
        build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider(result=result))


def test_is_deterministic():
    first = build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider())
    second = build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider())
    assert first == second


def test_changes_change_id():
    first = build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider())
    changed = Provider().result | {"changes": []}
    second = build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider(result=changed))
    assert first["editorial_cleanup_id"] != second["editorial_cleanup_id"]


def test_does_not_mutate_source():
    source = draft()
    before = copy.deepcopy(source)
    build_ai_content_cleaning(article_draft=source, llm_provider=Provider())
    assert source == before


def test_constraints_and_audit_are_fixed():
    result = build_ai_content_cleaning(article_draft=draft(), llm_provider=Provider())
    assert result["constraints"] == {
        "network_access": False,
        "provider_call": True,
        "source_mutation": False,
        "draft_mutation": False,
        "new_facts": False,
        "claim_rewriting": False,
        "structure_rewriting": False,
    }
    assert result["audit"] == {
        "method": "injected_llm_editorial_cleanup",
        "version": "v1",
        "validation_status": "validated",
    }
