from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.research.article_draft_agent import run


def _seed(tmp_path: Path, project: str = "draft-demo") -> Path:
    root = tmp_path / "research" / project
    root.mkdir(parents=True)
    (root / "keyword.json").write_text(
        json.dumps({"keyword": "best expat health insurance", "language": "en", "country": "US"}),
        encoding="utf-8",
    )
    (root / "metadata.json").write_text(
        json.dumps({"id": "rr_draft_demo", "project_name": project}), encoding="utf-8"
    )
    (root / "search-metrics.json").write_text(
        json.dumps({"search_volume": 1000, "competition": 0.2, "cpc": 2.5}),
        encoding="utf-8",
    )
    (root / "serp-analysis.json").write_text(
        json.dumps({
            "keyword": "best expat health insurance",
            "results": [
                {"position": 1, "domain": "example.com", "title": "Best Expat Health Insurance", "url": "https://example.com/guide"},
                {"position": 2, "domain": "example.org", "title": "Expat Health Insurance Plans", "url": "https://example.org/plans"},
            ],
        }),
        encoding="utf-8",
    )
    return root


def test_writer_agent_runs_full_downstream_path(tmp_path, monkeypatch):
    root = _seed(tmp_path)
    monkeypatch.chdir(tmp_path)

    draft = run("draft-demo")

    report = json.loads((root / "research-report.json").read_text())
    decision = json.loads((root / "decision.json").read_text())
    strategy = json.loads((root / "content-strategy.json").read_text())
    brief = json.loads((root / "content-brief.json").read_text())
    saved = json.loads((root / "article-draft.json").read_text())
    metadata = json.loads((root / "metadata.json").read_text())

    assert draft == saved
    assert decision["outcome"] == "approved"
    assert brief["lifecycle_stage"] == "content_brief_ready"
    assert saved["lifecycle_stage"] == "draft_ready"
    assert saved["brief_id"] == brief["brief_id"]
    assert saved["strategy_id"] == strategy["strategy_id"]
    assert saved["decision_id"] == decision["decision_id"]
    assert saved["report_id"] == report["report_id"]
    assert saved["evidence_refs"] == brief["evidence_refs"]
    assert metadata["status"] == "draft_ready"


def test_writer_agent_is_deterministic_and_does_not_mutate_upstream(tmp_path, monkeypatch):
    root = _seed(tmp_path, "stable-draft")
    monkeypatch.chdir(tmp_path)

    first = run("stable-draft")
    upstream_first = {
        name: (root / name).read_text()
        for name in [
            "research-report.json",
            "recommendation.json",
            "decision.json",
            "content-strategy.json",
            "content-brief.json",
        ]
    }

    second = run("stable-draft")
    upstream_second = {
        name: (root / name).read_text()
        for name in upstream_first
    }

    assert first == second
    assert first["draft_id"] == second["draft_id"]
    assert upstream_first == upstream_second


def test_writer_agent_requires_a_publishable_content_brief(tmp_path, monkeypatch):
    root = _seed(tmp_path, "guarded-draft")
    monkeypatch.chdir(tmp_path)

    (root / "content-brief.json").write_text(
        json.dumps({
            "brief_id": "brief_guard",
            "report_id": "rr_guard",
            "decision_id": "dec_guard",
            "strategy_id": "strat_guard",
            "lifecycle_stage": "draft_ready",
            "evidence_refs": ["ev_guard"],
            "outline": [{"section": "Intro", "purpose": "Introduce the topic"}],
            "content_type": "guide",
            "primary_keyword": "guarded keyword",
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="content_brief_ready"):
        from agents.research.article_draft import build_article_draft
        build_article_draft(content_brief=json.loads((root / "content-brief.json").read_text()))
