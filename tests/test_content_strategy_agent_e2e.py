import json
from pathlib import Path

from agents.research.agent import run
from agents.research.content_strategy_runner import run_content_strategy_from_report


def _seed_project(tmp_path: Path) -> Path:
    project = "demo"
    root = tmp_path / "research" / project
    root.mkdir(parents=True)
    (root / "keyword.json").write_text(json.dumps({"keyword": "best expat health insurance", "language": "en", "country": "US"}))
    (root / "metadata.json").write_text(json.dumps({"id": "rr_demo", "project_name": project}))
    (root / "search-metrics.json").write_text(json.dumps({"search_volume": 1000, "competition": 0.2, "cpc": 2.5}))
    (root / "serp-analysis.json").write_text(json.dumps({"keyword": "best expat health insurance", "results": []}))
    return root


def test_content_strategy_runs_after_decision(monkeypatch, tmp_path):
    root = _seed_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    run("demo")

    report = json.loads((root / "research-report.json").read_text())
    decision = json.loads((root / "decision.json").read_text())
    strategy = json.loads((root / "content-strategy.json").read_text())

    assert decision["outcome"] == "approved"
    assert strategy["lifecycle_stage"] == "content_strategy_ready"
    assert strategy["report_id"] == report["report_id"]
    assert strategy["decision_id"] == decision["decision_id"]
    assert strategy["evidence_refs"] == decision["evidence_refs"]
    assert strategy["primary_keyword"] == "best expat health insurance"
    assert strategy["sections"]
    expected_entities = [
        item.get("name") or item.get("entity")
        for item in report["entity_analysis"].get("entities", [])
        if isinstance(item, dict) and (item.get("name") or item.get("entity"))
    ]
    assert strategy["entities"] == list(dict.fromkeys(expected_entities))
    assert strategy["questions"] == report["question_analysis"].get("questions", [])
    assert json.loads((root / "metadata.json").read_text())["status"] == "content_strategy_ready"


def test_content_strategy_is_stable_on_second_run(monkeypatch, tmp_path):
    root = _seed_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    run("demo")
    first = json.loads((root / "content-strategy.json").read_text())
    run("demo")
    second = json.loads((root / "content-strategy.json").read_text())

    assert first == second


def test_content_strategy_cannot_bypass_decision(tmp_path):
    report = {"report_id": "rr_demo", "lifecycle_stage": "research_complete"}
    decision = {
        "decision_id": "dec_demo",
        "report_id": "rr_demo",
        "lifecycle_stage": "decision_ready",
        "outcome": "rejected",
        "evidence_refs": ["ev_1"],
    }

    try:
        run_content_strategy_from_report(report, decision)
    except ValueError as exc:
        assert "approved Decision" in str(exc)
    else:
        raise AssertionError("Content Strategy must not bypass an approved Decision")
