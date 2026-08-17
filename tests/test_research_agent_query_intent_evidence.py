import json
from pathlib import Path

import agents.research.agent as research_agent


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_research_agent_writes_query_intent_evidence_end_to_end(tmp_path, monkeypatch):
    project_name = "demo-project"
    project_dir = tmp_path / "research" / project_name

    _write_json(project_dir / "keyword.json", {"keyword": "expat health insurance", "language": "en", "country": "US"})
    _write_json(project_dir / "metadata.json", {
        "id": "rr_demo_001", "keyword": "expat health insurance", "language": "en", "country": "US",
        "created_at": "2026-08-17T00:00:00Z", "updated_at": "2026-08-17T00:00:00Z", "version": "1.0",
        "status": "draft", "project_name": project_name,
    })
    _write_json(project_dir / "search-metrics.json", {"keyword": "expat health insurance", "volume": 1000})
    _write_json(project_dir / "serp-analysis.json", {
        "keyword": "expat health insurance", "language": "en", "country": "US",
        "results": [
            {"position": 1, "domain": "example.com", "title": "Expat Health Insurance Guide", "snippet": "Learn about coverage and requirements.", "url": "https://example.com/guide?utm_source=test"},
            {"position": 2, "domain": "example.org", "title": "Best Expat Health Insurance Plans", "snippet": "Compare plans and pricing.", "url": "https://example.org/plans?utm_medium=test"},
        ],
    })

    monkeypatch.chdir(tmp_path)
    research_agent.run(project_name)

    analysis = json.loads((project_dir / "query-intent-analysis.json").read_text(encoding="utf-8"))
    evidence = json.loads((project_dir / "query-intent-evidence.json").read_text(encoding="utf-8"))
    metadata = json.loads((project_dir / "metadata.json").read_text(encoding="utf-8"))

    assert evidence["report_id"] == "rr_demo_001"
    assert evidence["domain"] == "intent"
    assert evidence["claim"] == {"type": "query_intent", "attribute": "primary_intent"}
    assert evidence["value"]["data"] == analysis["primary_intent"]
    assert evidence["confidence"] == analysis["confidence"]
    assert evidence["provenance"]["analyzer"] == "query_intent"
    assert evidence["evidence_id"].startswith("ev_")
    assert evidence["status"] == "active"
    assert metadata["status"] == "recommendation_ready"


def test_research_agent_uses_stable_fallback_report_id(tmp_path, monkeypatch):
    project_name = "fallback-project"
    project_dir = tmp_path / "research" / project_name

    _write_json(project_dir / "keyword.json", {"keyword": "consultant insurance", "language": "en", "country": "US"})
    _write_json(project_dir / "metadata.json", {"id": "", "status": "draft", "project_name": project_name})
    _write_json(project_dir / "search-metrics.json", {})
    _write_json(project_dir / "serp-analysis.json", {"keyword": "consultant insurance", "language": "en", "country": "US", "results": []})

    monkeypatch.chdir(tmp_path)
    research_agent.run(project_name)

    evidence = json.loads((project_dir / "query-intent-evidence.json").read_text(encoding="utf-8"))
    assert evidence["report_id"] == "rr_fallback-project"
