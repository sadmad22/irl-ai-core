import pytest

from agents.research.article_configuration import build_article_config


def brief(**overrides):
    value = {
        "brief_id": "brief-1",
        "report_id": "report-1",
        "decision_id": "decision-1",
        "strategy_id": "strategy-1",
        "lifecycle_stage": "content_brief_ready",
        "content_type": "guide",
    }
    value.update(overrides)
    return value


def test_builds_standard_config_from_content_brief():
    config = build_article_config(content_brief=brief(), target_country="United States")
    assert config["lifecycle_stage"] == "article_config_ready"
    assert config["article_type"] == "guide"
    assert config["article_size"] == "standard"
    assert config["target_country"] == "United States"
    assert config["word_target"] == {"min": 1400, "target": 2000, "max": 2600}
    assert config["heading_target"] == {"min": 6, "target": 8, "max": 10}


def test_article_type_is_derived_from_content_brief():
    config = build_article_config(content_brief=brief(content_type="comparison"), target_country="US")
    assert config["article_type"] == "comparison"


def test_size_profile_changes_targets():
    short = build_article_config(content_brief=brief(), target_country="US", article_size="short")
    long = build_article_config(content_brief=brief(), target_country="US", article_size="long")
    assert short["word_target"]["target"] < long["word_target"]["target"]
    assert short["heading_target"]["target"] < long["heading_target"]["target"]


def test_explicit_targets_override_size_defaults():
    config = build_article_config(
        content_brief=brief(),
        target_country="US",
        word_target={"min": 1000, "target": 1500, "max": 1800},
        heading_target={"min": 5, "target": 7, "max": 9},
    )
    assert config["word_target"]["target"] == 1500
    assert config["heading_target"]["target"] == 7


def test_target_country_is_required():
    with pytest.raises(ValueError, match="target_country"):
        build_article_config(content_brief=brief(), target_country=" ")


def test_requires_ready_content_brief():
    with pytest.raises(ValueError, match="content_brief_ready"):
        build_article_config(content_brief=brief(lifecycle_stage="draft"), target_country="US")


def test_rejects_unsupported_article_type():
    with pytest.raises(ValueError, match="supported article types"):
        build_article_config(content_brief=brief(content_type="news"), target_country="US")


def test_rejects_invalid_size():
    with pytest.raises(ValueError, match="article_size"):
        build_article_config(content_brief=brief(), target_country="US", article_size="huge")


def test_rejects_invalid_word_range():
    with pytest.raises(ValueError, match="word_target"):
        build_article_config(
            content_brief=brief(),
            target_country="US",
            word_target={"min": 2000, "target": 1500, "max": 2500},
        )


def test_config_id_is_deterministic():
    first = build_article_config(content_brief=brief(), target_country="US")
    second = build_article_config(content_brief=brief(), target_country="US")
    assert first["config_id"] == second["config_id"]


def test_country_changes_config_identity():
    us = build_article_config(content_brief=brief(), target_country="US")
    uk = build_article_config(content_brief=brief(), target_country="UK")
    assert us["config_id"] != uk["config_id"]
