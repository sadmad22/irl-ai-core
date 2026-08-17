import json
from pathlib import Path

import agents.research.agent as research_agent


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_research_agent_writes_strategy_signal_evidence_end_to_end(tmp_path, monkeypatch):
    project_name = "strategy-project"
    project_dir = tmp_path / "research" / project_name

    _write_json(
        project_dir / "keyword.json",
        {"keyword": "expat health insurance", "language": "en", "country": "US"},
    )
    _write_json(
        project_dir / "metadata.json",
        {"id": "rr_strategy_001", "status": "draft", "project_name": project_name},
    )
    _write_json(project_dir / "search-metrics.json", {})
    _write_json(
        project_dir / "serp-analysis.json",
        {
            "keyword": "expat health insurance",
            "language": "en",
            "country": "US",
            "results": [
                {"position": 1, "domain": "example.com", "title": "Guide", "url": "https://example.com/guide"},
                {"position": 2, "domain": "example.org", "title": "Plans", "url": "https://example.org/plans"},
                {"position": 3, "domain": "example.net", "title": "How it works", "url": "https://example.net/how-it-works"},
            ],
        },
    )

    monkeypatch.chdir(tmp_path)
    research_agent.run(project_name)

    alignment = json.loads((project_dir / "intent-alignment-evidence.json").read_text(encoding="utf-8"))
    strategy = json.loads((project_dir / "serp-strategy-signal-evidence.json").read_text(encoding="utf-8"))

    assert strategy["report_id"] == "rr_strategy_001"
    assert strategy["type"] == "derived"
    assert strategy["domain"] == "serp"
    assert strategy["claim"] == {
        "type": "serp_strategy_signal",
        "attribute": "strategy_signal",
    }
    assert strategy["derived_from"] == [alignment["evidence_id"]]
    assert strategy["provenance"]["analyzer"] == "serp_strategy_signal"


def test_research_agent_strategy_signal_evidence_is_stable(tmp_path, monkeypatch):
    project_name = "stable-strategy-project"
    project_dir = tmp_path / "research" / project_name

    _write_json(
        project_dir / "keyword.json",
        {"keyword": "consultant insurance", "language": "en", "country": "US"},
    )
    _write_json(
        project_dir / "metadata.json",
        {"id": "rr_stable_strategy", "status": "draft", "project_name": project_name},
    )
    _write_json(project_dir / "search-metrics.json", {})
    _write_json(
        project_dir / "serp-analysis.json",
        {
            "keyword": "consultant insurance",
            "language": "en",
            "country": "US",
            "results": [
                {"position": 1, "domain": "example.com", "title": "Consultant Insurance", "url": "https://example.com/insurance"}
            ],
        },
    )

    monkeypatch.chdir(tmp_path)
    research_agent.run(project_name)
    first = json.loads((project_dir / "serp-strategy-signal-evidence.json").read_text(encoding="utf-8"))

    research_agent.run(project_name)
    second = json.loads((project_dir / "serp-strategy-signal-evidence.json").read_text(encoding="utf-8"))

    assert first["evidence_id"] == second["evidence_id"]
    assert first["derived_from"] == second["derived_from"]
    assert first["report_id"] == second["report_id"]
