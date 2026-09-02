import json

from tools.live_preview import server


def _brief():
    return {
        "brief_id": "brief-1",
        "report_id": "report-1",
        "decision_id": "decision-1",
        "strategy_id": "strategy-1",
        "schema_version": "1.0",
        "lifecycle_stage": "content_brief_ready",
        "content_type": "guide",
        "primary_keyword": "expat health insurance",
        "search_intent": "informational",
        "audience": "Expats comparing insurance",
        "objective": "Provide trustworthy guidance.",
        "title_direction": "A practical guide",
        "outline": [{"heading": "Coverage", "purpose": "Explain coverage."}],
        "required_entities": [],
        "required_questions": [],
        "evidence_refs": ["evidence-1"],
        "editorial_constraints": [],
    }


def _strategy():
    return {
        "strategy_id": "strategy-1",
        "report_id": "report-1",
        "decision_id": "decision-1",
        "brief_id": "brief-1",
        "schema_version": "1.0",
        "lifecycle_stage": "content_strategy_ready",
        "content_type": "guide",
        "primary_keyword": "expat health insurance",
        "audience": "Expats comparing international health insurance",
        "angle": "Evidence-led comparison",
        "format": "structured guide",
        "sections": ["Coverage", "Costs", "Providers"],
        "entities": ["Cigna Global", "Allianz Care"],
        "questions": ["How much does expat health insurance cost?"],
        "business_goal": "Build qualified organic traffic.",
        "evidence_refs": ["evidence-1"],
    }


def _report(country=""):
    return {
        "report_id": "report-1",
        "schema_version": "1.0",
        "lifecycle_stage": "research_complete",
        "metadata": {"country": country, "project_name": "preview-test"},
    }


def _write_project(tmp_path, *, country=""):
    project = tmp_path / "preview-test"
    project.mkdir()
    (project / "content-brief.json").write_text(json.dumps(_brief()), encoding="utf-8")
    (project / "content-strategy.json").write_text(json.dumps(_strategy()), encoding="utf-8")
    (project / "research-report.json").write_text(json.dumps(_report(country)), encoding="utf-8")
    return project


def test_semantic_seo_is_computed_through_core_contract(tmp_path, monkeypatch):
    _write_project(tmp_path)
    monkeypatch.setattr(server, "RESEARCH_ROOT", tmp_path)

    payload = server._project_payload("preview-test")
    semantic = next(item for item in payload["artifacts"] if item["name"] == "Semantic SEO")

    assert semantic["status"] == "computed"
    assert semantic["source"] == "core_contract"
    assert semantic["data"]["lifecycle_stage"] == "semantic_seo_ready"
    assert semantic["data"]["strategy_id"] == "strategy-1"


def test_article_config_is_blocked_when_country_is_not_explicit(tmp_path, monkeypatch):
    _write_project(tmp_path)
    monkeypatch.setattr(server, "RESEARCH_ROOT", tmp_path)

    payload = server._project_payload("preview-test")
    config = next(item for item in payload["artifacts"] if item["name"] == "Article Configuration")

    assert config["status"] == "blocked"
    assert "target_country" in config["reason"]


def test_article_config_is_computed_from_real_core_contract(tmp_path, monkeypatch):
    _write_project(tmp_path, country="US")
    monkeypatch.setattr(server, "RESEARCH_ROOT", tmp_path)

    payload = server._project_payload("preview-test")
    config = next(item for item in payload["artifacts"] if item["name"] == "Article Configuration")

    assert config["status"] == "computed"
    assert config["source"] == "core_contract"
    assert config["data"]["lifecycle_stage"] == "article_config_ready"
    assert config["data"]["target_country"] == "US"


def test_materialized_artifact_remains_the_source_of_truth(tmp_path, monkeypatch):
    project = _write_project(tmp_path, country="US")
    expected = {"lifecycle_stage": "article_config_ready", "config_id": "persisted-1"}
    (project / "article-config.json").write_text(json.dumps(expected), encoding="utf-8")
    monkeypatch.setattr(server, "ARTIFACTS", {**server.ARTIFACTS, "Article Configuration": "article-config.json"})
    monkeypatch.setattr(server, "RESEARCH_ROOT", tmp_path)

    payload = server._project_payload("preview-test")
    config = next(item for item in payload["artifacts"] if item["name"] == "Article Configuration")

    assert config["status"] == "available"
    assert config["source"] == "materialized_artifact"
    assert config["data"] == expected


def test_preview_does_not_persist_computed_contracts(tmp_path, monkeypatch):
    project = _write_project(tmp_path, country="US")
    monkeypatch.setattr(server, "RESEARCH_ROOT", tmp_path)

    server._project_payload("preview-test")

    assert not (project / "article-config.json").exists()
    assert not (project / "semantic-seo.json").exists()
