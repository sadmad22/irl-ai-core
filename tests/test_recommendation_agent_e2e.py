import json
from pathlib import Path

from agents.research.agent import run
from agents.research.recommendation_runner import run_recommendation_from_report


def _all_refs(report):
    refs = []
    for values in report["evidence_refs"].values():
        refs.extend(values)
    return list(dict.fromkeys(refs))


def test_recommendation_is_integrated_into_research_agent(monkeypatch, tmp_path):
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
    recommendation = json.loads((root / "recommendation.json").read_text())
    metadata = json.loads((root / "metadata.json").read_text())

    assert report["lifecycle_stage"] == "research_complete"
    assert report["recommendation"] is None
    assert report["decision"] is None
    assert recommendation["report_id"] == report["report_id"]
    assert recommendation["lifecycle_stage"] == "recommendation_ready"
    assert recommendation["evidence_refs"] == _all_refs(report)
    assert metadata["status"] in {"decision_ready", "content_strategy_ready"}


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
        "competitor_analysis": {"domain_counts": {"example.com": 1, "other.com": 1}},
        "business_analysis": {"commercial_value": "high"},
        "topical_authority": {"authority_score": 0.9, "topic_fit": 0.9},
    }
    first = run_recommendation_from_report(report)
    second = run_recommendation_from_report(report)
    assert first == second
