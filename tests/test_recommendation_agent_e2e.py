import json
from pathlib import Path

from agents.research.agent import run
from agents.research.recommendation_runner import run_recommendation_from_report


def test_recommendation_runs_from_canonical_report(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    project = "demo"
    root = Path("research") / project
    root.mkdir(parents=True)
    (root / "keyword.json").write_text(json.dumps({"keyword": "best expat health insurance", "language": "en", "country": "US"}))
    (root / "metadata.json").write_text(json.dumps({"id": "rr_demo", "project_name": project}))
    (root / "search-metrics.json").write_text(json.dumps({"search_volume": 1000, "competition": 0.2, "cpc": 2.5}))
    (root / "serp-analysis.json").write_text(json.dumps({"keyword": "best expat health insurance", "results": []}))

    run(project)
    report = json.loads((root / "research-report.json").read_text())
    recommendation = run_recommendation_from_report(report)

    assert recommendation["report_id"] == "rr_demo"
    assert recommendation["lifecycle_stage"] == "recommendation_ready"
    assert recommendation["decision"] is None
    assert recommendation["evidence_refs"] == report["evidence_refs"]["intent"]


def test_recommendation_is_stable_for_same_report(tmp_path):
    report = {
        "report_id": "rr_stable",
        "lifecycle_stage": "research_complete",
        "recommendation": None,
        "decision": None,
        "evidence_refs": {
            "intent": ["ev_q", "ev_s", "ev_a", "ev_strategy"],
            "entity": ["ev_e"],
            "question": ["ev_question"],
            "business": ["ev_business"],
            "authority": ["ev_authority"],
        },
        "search_intent": {"primary_intent": "Commercial", "confidence": 0.9},
        "serp_analysis": {"results": [{"position": 1}, {"position": 2}]},
        "business_analysis": {"commercial_value": "high"},
        "topical_authority": {"score": 0.9},
    }
    first = run_recommendation_from_report(report)
    second = run_recommendation_from_report(report)
    assert first == second
