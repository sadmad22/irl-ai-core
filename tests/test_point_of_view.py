from __future__ import annotations

import copy

import pytest

from agents.research.point_of_view import build_point_of_view


def strategy(**overrides):
    value = {
        "brief_id": "brief_1",
        "report_id": "report_1",
        "decision_id": "decision_1",
        "strategy_id": "strategy_1",
        "lifecycle_stage": "content_strategy_ready",
        "intent": "informational",
        "content_type": "guide",
    }
    value.update(overrides)
    return value


def config(**overrides):
    value = {
        "brief_id": "brief_1",
        "report_id": "report_1",
        "decision_id": "decision_1",
        "strategy_id": "strategy_1",
        "config_id": "config_1",
        "lifecycle_stage": "article_config_ready",
        "article_type": "guide",
    }
    value.update(overrides)
    return value


def test_builds_ready_contract():
    result = build_point_of_view(content_strategy=strategy(), article_config=config())
    assert result["lifecycle_stage"] == "point_of_view_ready"
    assert result["point_of_view"]["primary"] == "second_person"
    assert result["point_of_view"]["stance"] == "expert_explanatory"
    assert result["point_of_view"]["pronoun_policy"] == "use_you"
    assert result["constraints"]["network_access"] is False
    assert result["audit"]["validation_status"] == "validated"


def test_comparison_prefers_third_person_editorial_neutral():
    result = build_point_of_view(content_strategy=strategy(content_type="comparison"), article_config=config(article_type="comparison"))
    assert result["point_of_view"] == {
        "primary": "third_person",
        "stance": "editorial_neutral",
        "pronoun_policy": "avoid_first_person",
    }


def test_buyer_guide_uses_second_person():
    result = build_point_of_view(content_strategy=strategy(intent="transactional", content_type="buyer_guide"), article_config=config(article_type="buyer_guide"))
    assert result["point_of_view"]["primary"] == "second_person"
    assert result["point_of_view"]["pronoun_policy"] == "use_you"


def test_article_defaults_to_third_person():
    result = build_point_of_view(content_strategy=strategy(intent="navigational", content_type="article"), article_config=config(article_type="article"))
    assert result["point_of_view"]["primary"] == "third_person"


def test_preserves_lineage():
    result = build_point_of_view(content_strategy=strategy(), article_config=config())
    for field in ("brief_id", "report_id", "decision_id", "strategy_id"):
        assert result[field] == strategy()[field]
    assert result["config_id"] == config()["config_id"]


def test_deterministic_id():
    a = build_point_of_view(content_strategy=strategy(), article_config=config())
    b = build_point_of_view(content_strategy=strategy(), article_config=config())
    assert a["point_of_view_id"] == b["point_of_view_id"]


def test_does_not_mutate_inputs():
    s, c = strategy(), config()
    original_s, original_c = copy.deepcopy(s), copy.deepcopy(c)
    build_point_of_view(content_strategy=s, article_config=c)
    assert s == original_s
    assert c == original_c


@pytest.mark.parametrize("field", ["brief_id", "report_id", "decision_id", "strategy_id"])
def test_rejects_missing_strategy_lineage(field):
    value = strategy()
    value.pop(field)
    with pytest.raises(ValueError, match=field):
        build_point_of_view(content_strategy=value, article_config=config())


@pytest.mark.parametrize("field", ["brief_id", "report_id", "decision_id", "strategy_id"])
def test_rejects_lineage_mismatch(field):
    value = config()
    value[field] = "different"
    with pytest.raises(ValueError, match="Lineage mismatch"):
        build_point_of_view(content_strategy=strategy(), article_config=value)


def test_rejects_wrong_strategy_lifecycle():
    with pytest.raises(ValueError, match="content_strategy_ready"):
        build_point_of_view(content_strategy=strategy(lifecycle_stage="draft"), article_config=config())


def test_rejects_wrong_config_lifecycle():
    with pytest.raises(ValueError, match="article_config_ready"):
        build_point_of_view(content_strategy=strategy(), article_config=config(lifecycle_stage="draft"))


def test_rejects_missing_config_id():
    value = config()
    value.pop("config_id")
    with pytest.raises(ValueError, match="config_id"):
        build_point_of_view(content_strategy=strategy(), article_config=value)


def test_rejects_invalid_intent():
    with pytest.raises(ValueError, match="Unsupported content strategy intent"):
        build_point_of_view(content_strategy=strategy(intent="invalid"), article_config=config())


def test_rejects_invalid_article_type():
    with pytest.raises(ValueError, match="Unsupported article type"):
        build_point_of_view(content_strategy=strategy(), article_config=config(article_type="invalid"))


def test_schema_contract_is_stable():
    result = build_point_of_view(content_strategy=strategy(), article_config=config())
    assert set(result) == {
        "point_of_view_id", "brief_id", "report_id", "decision_id", "strategy_id", "config_id",
        "schema_version", "lifecycle_stage", "point_of_view", "editorial_guidance", "constraints", "audit",
    }


def test_guidance_is_specific_and_nonempty():
    result = build_point_of_view(content_strategy=strategy(), article_config=config())
    guidance = result["editorial_guidance"]
    assert guidance["preferred_patterns"]
    assert guidance["avoid_patterns"]
    assert guidance["consistency_rules"]
