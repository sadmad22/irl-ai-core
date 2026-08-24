import json
from pathlib import Path

import agents.research.content_research_pipeline as pipeline


def _write_json(root: Path, filename: str, payload: dict) -> None:
    (root / filename).write_text(json.dumps(payload), encoding="utf-8")


def test_research_to_content_vertical_slice(monkeypatch, tmp_path):
    project = "vertical-slice"
    research_dir = tmp_path / "research" / project
    research_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    _write_json(research_dir, "metadata.json", {"project_name": project, "status": "researching"})

    def fake_research(project_name: str) -> None:
        assert project_name == project
        _write_json(research_dir, "research-report.json", {"report_id": "report-1"})
        _write_json(research_dir, "question-analysis.json", {"questions": ["What is the core question?"]})
        _write_json(research_dir, "source-evidence.json", {"evidence_id": "e1"})

    def fake_article_draft(project_name: str) -> None:
        assert project_name == project
        _write_json(
            research_dir,
            "content-brief.json",
            {
                "brief_id": "brief-1",
                "report_id": "report-1",
                "decision_id": "decision-1",
                "strategy_id": "strategy-1",
                "lifecycle_stage": "content_brief_ready",
                "primary_keyword": "test topic",
                "content_type": "guide",
                "evidence_refs": ["e1"],
                "outline": [{"heading": "Overview", "purpose": "Answer the core question."}],
            },
        )
        _write_json(
            research_dir,
            "article-draft.json",
            {
                "draft_id": "draft-1",
                "brief_id": "brief-1",
                "report_id": "report-1",
                "decision_id": "decision-1",
                "strategy_id": "strategy-1",
                "lifecycle_stage": "draft_ready",
            },
        )

    monkeypatch.setattr(pipeline, "run_research_agent", fake_research)
    monkeypatch.setattr(pipeline, "run_article_draft_agent", fake_article_draft)
    monkeypatch.setattr(
        pipeline,
        "build_content_research_to_wordpress_draft",
        lambda **kwargs: {
            "research_report": kwargs["research_report"],
            "content_brief": kwargs["content_brief"],
            "article_draft": kwargs["article_draft"],
            "article_draft_quality": {"outcome": "passed"},
            "claim_audit": {"outcome": "passed"},
            "publication": {"gate_status": "allowed"},
        },
    )

    result = pipeline.run_content_research_to_wordpress_draft(project)

    assert result["research_report"]["report_id"] == "report-1"
    assert result["content_brief"]["brief_id"] == "brief-1"
    assert result["article_draft"]["draft_id"] == "draft-1"
    assert result["article_draft_quality"]["outcome"] == "passed"
    assert result["claim_audit"]["outcome"] == "passed"
    assert json.loads((research_dir / "research-sufficiency.json").read_text())["passed"] is True
