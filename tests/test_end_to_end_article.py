import json
from pathlib import Path

import agents.research.article_draft_agent as article_draft_agent
import agents.research.content_research_pipeline as pipeline


def _write_json(root: Path, filename: str, payload: dict) -> None:
    (root / filename).write_text(json.dumps(payload), encoding="utf-8")


def test_end_to_end_article_reaches_wordpress_draft_ready(monkeypatch, tmp_path):
    project = "end-to-end-article"
    research_dir = tmp_path / "research" / project
    research_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    _write_json(research_dir, "metadata.json", {"project_name": project, "status": "researching"})

    def fake_research(project_name: str) -> None:
        assert project_name == project
        _write_json(research_dir, "research-report.json", {"report_id": "report-1"})
        _write_json(research_dir, "question-analysis.json", {"questions": ["What is the core question?"]})
        _write_json(research_dir, "source-evidence.json", {"evidence_id": "e1", "domain": "insurance", "claim": {"attribute": "coverage"}, "value": {"data": "supported"}, "subject": {"id": "topic"}})
        _write_json(research_dir, "decision.json", {"decision_id": "decision-1"})
        _write_json(research_dir, "content-strategy.json", {"strategy_id": "strategy-1"})

    def fake_content_brief(project_name: str) -> dict:
        assert project_name == project
        brief = {"brief_id": "brief-1", "report_id": "report-1", "decision_id": "decision-1", "strategy_id": "strategy-1", "lifecycle_stage": "content_brief_ready", "primary_keyword": "test topic", "content_type": "guide", "evidence_refs": ["e1"], "outline": [{"heading": "Introduction", "purpose": "Answer the core question."}], "editorial_constraints": []}
        _write_json(research_dir, "content-brief.json", brief)
        return brief

    monkeypatch.setattr(pipeline, "run_research_agent", fake_research)
    monkeypatch.setattr(article_draft_agent, "run_content_brief_agent", fake_content_brief)
    monkeypatch.setattr(pipeline, "run_seo_strategy_agent", lambda **kwargs: {"strategy_id": "seo-1"})
    monkeypatch.setattr(pipeline, "run_seo_validation_agent", lambda **kwargs: {"outcome": "passed"})
    monkeypatch.setattr(pipeline, "build_editorial_review", lambda **kwargs: {"outcome": "passed"})
    monkeypatch.setattr(pipeline, "run_publication_agent", lambda **kwargs: {"gate_status": "allowed"})
    monkeypatch.setattr(pipeline, "run_publisher_agent", lambda **kwargs: {"status": "ready"})
    monkeypatch.setattr(pipeline, "run_wordpress_draft_delivery_agent", lambda **kwargs: {"status": "prepared"})

    result = pipeline.run_content_research_to_wordpress_draft(project)

    assert result["research_sufficiency"]["passed"] is True
    assert result["content_brief"]["lifecycle_stage"] == "content_brief_ready"
    assert result["article_draft"]["lifecycle_stage"] == "draft_ready"
    assert result["article_draft"]["sections"][0]["claims"][0]["grounding_status"] == "grounded"
    assert result["article_draft_quality"]["outcome"] == "passed"
    assert result["claim_audit"]["outcome"] == "passed"
    assert result["seo_validation"]["outcome"] == "passed"
    assert result["editorial_review"]["outcome"] == "passed"
    assert result["publication"]["gate_status"] == "allowed"
    assert result["wordpress_draft_delivery"]["status"] == "prepared"
    assert json.loads((research_dir / "metadata.json").read_text())["status"] == "wordpress_draft_ready"
