import json
from pathlib import Path

import pytest

from agents.research.content_brief_agent import run
from agents.research.content_brief_runner import run_content_brief_from_artifacts


def _seed(tmp_path: Path, project: str = "brief-demo") -> Path:
    root = tmp_path / "research" / project
    root.mkdir(parents=True)
    (root / "keyword.json").write_text(
        json.dumps({"keyword": "best expat health insurance", "language": "en", "country": "US"}),
        encoding="utf-8",
    )
    (root / "metadata.json").write_text(
        json.dumps({"id": "rr_brief_demo", "project_name": project}), encoding="utf-8"
    )
    (root / "search-metrics.json").write_text(
        json.dumps({"search_volume": 1000, "competition": 0.2, "cpc": 2.5}), encoding="utf-8"
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


def test_content_brief_agent_runs_full_downstream_path(tmp_path, monkeypatch):
    root = _seed(tmp_path)
    monkeypatch.chdir(tmp_path)

    brief = run("brief-demo")

    report = json.loads((root / "research-report.json").read_text())
    decision = json.loads((root / "decision.json").read_text())
    strategy = json.loads((root / "content-strategy.json").read_text())
    saved = json.loads((root / "content-brief.json").read_text())
    metadata = json.loads((root / "metadata.json").read_text())

    assert brief == saved
    assert decision["outcome"] == "approved"
    assert strategy["lifecycle_stage"] == "content_strategy_ready"
    assert saved["lifecycle_stage"] == "content_brief_ready"
    assert saved["report_id"] == report["report_id"]
    assert saved["decision_id"] == decision["decision_id"]
    assert saved["strategy_id"] == strategy["strategy_id"]
    assert saved["evidence_refs"] == strategy["evidence_refs"]
    assert metadata["status"] == "content_brief_ready"


def test_content_brief_agent_is_deterministic(tmp_path, monkeypatch):
    _seed(tmp_path, "stable-brief")
    monkeypatch.chdir(tmp_path)

    first = run("stable-brief")
    second = run("stable-brief")

    assert first == second
    assert first["brief_id"] == second["brief_id"]
    assert first["evidence_refs"] == second["evidence_refs"]
    assert first["report_id"] == second["report_id"]


def test_content_brief_runner_rejects_non_approved_decision():
    report = {"report_id": "rr_guard", "lifecycle_stage": "research_complete"}
    decision = {
        "report_id": "rr_guard",
        "decision_id": "dec_guard",
        "lifecycle_stage": "decision_ready",
        "outcome": "deferred",
    }
    strategy = {
        "report_id": "rr_guard",
        "decision_id": "dec_guard",
        "strategy_id": "strat_guard",
        "lifecycle_stage": "content_strategy_ready",
        "evidence_refs": ["ev_1"],
    }

    with pytest.raises(ValueError, match="approved"):
        run_content_brief_from_artifacts(
            research_report=report,
            decision=decision,
            content_strategy=strategy,
        )
