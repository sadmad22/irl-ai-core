import json
from pathlib import Path

import pytest

from agents.research.agent import run
from agents.research.decision_runner import run_decision_from_report
from agents.research.recommendation_runner import run_recommendation_from_report


def _seed_project(tmp_path: Path, project: str = "demo") -> Path:
    root = tmp_path / "research" / project
    root.mkdir(parents=True)
    (root / "keyword.json").write_text(
        json.dumps({"keyword": "best expat health insurance", "language": "en", "country": "US"})
    )
    (root / "metadata.json").write_text(json.dumps({"id": "rr_demo", "project_name": project}))
    (root / "search-metrics.json").write_text(json.dumps({"search_volume": 1000, "competition": 0.2, "cpc": 2.5}))
    (root / "serp-analysis.json").write_text(
        json.dumps({"keyword": "best expat health insurance", "results": []})
    )
    return root


def test_decision_is_integrated_end_to_end(monkeypatch, tmp_path):
    root = _seed_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    run("demo")

    report = json.loads((root / "research-report.json").read_text())
    recommendation = json.loads((root / "recommendation.json").read_text())
    decision = json.loads((root / "decision.json").read_text())
    metadata = json.loads((root / "metadata.json").read_text())

    assert report["lifecycle_stage"] == "research_complete"
    assert recommendation["lifecycle_stage"] == "recommendation_ready"
    assert decision["lifecycle_stage"] == "decision_ready"
    assert decision["report_id"] == report["report_id"]
    assert decision["recommendation_id"] == recommendation["recommendation_id"]
    assert decision["recommendation_ref"] == recommendation["recommendation_id"]
    assert decision["evidence_refs"] == recommendation["evidence_refs"]
    assert metadata["status"] in {"decision_ready", "content_strategy_ready"}


def test_decision_preserves_strict_recommendation_transition(tmp_path):
    report = {
        "report_id": "rr_stable",
        "lifecycle_stage": "research_complete",
        "recommendation": None,
        "decision": None,
    }
    recommendation = {
        "report_id": "rr_stable",
        "recommendation_id": "rec_001",
        "lifecycle_stage": "recommendation_ready",
        "recommendation": "pursue",
        "evidence_refs": ["ev_intent", "ev_business"],
    }

    decision = run_decision_from_report(report, recommendation)

    assert decision["outcome"] == "approved"
    assert decision["recommendation_id"] == "rec_001"
    assert decision["evidence_refs"] == ["ev_intent", "ev_business"]
    assert decision["audit"]["method"] == "recommendation_to_decision_transition"


def test_decision_is_deterministic_for_same_inputs():
    report = {
        "report_id": "rr_stable",
        "lifecycle_stage": "research_complete",
        "recommendation": None,
        "decision": None,
    }
    recommendation = {
        "report_id": "rr_stable",
        "recommendation_id": "rec_001",
        "lifecycle_stage": "recommendation_ready",
        "recommendation": "defer",
        "evidence_refs": ["ev_intent", "ev_authority"],
    }

    first = run_decision_from_report(report, recommendation)
    second = run_decision_from_report(report, recommendation)

    assert first == second
    assert first["outcome"] == "deferred"


def test_decision_cannot_bypass_recommendation(tmp_path):
    report = {
        "report_id": "rr_no_rec",
        "lifecycle_stage": "research_complete",
        "recommendation": None,
        "decision": None,
    }
    recommendation = {
        "report_id": "rr_no_rec",
        "recommendation_id": "",
        "lifecycle_stage": "research_complete",
        "recommendation": "pursue",
        "evidence_refs": ["ev_1"],
    }

    with pytest.raises(ValueError, match="recommendation_ready"):
        run_decision_from_report(report, recommendation)


def test_decision_rejects_report_recommendation_mismatch():
    report = {
        "report_id": "rr_1",
        "lifecycle_stage": "research_complete",
        "recommendation": None,
        "decision": None,
    }
    recommendation = {
        "report_id": "rr_2",
        "recommendation_id": "rec_1",
        "lifecycle_stage": "recommendation_ready",
        "recommendation": "pursue",
        "evidence_refs": ["ev_1"],
    }

    with pytest.raises(ValueError, match="must match"):
        run_decision_from_report(report, recommendation)


def test_decision_does_not_mutate_canonical_report():
    report = {
        "report_id": "rr_immutable",
        "lifecycle_stage": "research_complete",
        "recommendation": None,
        "decision": None,
        "evidence_refs": {"intent": ["ev_1"]},
    }
    recommendation = {
        "report_id": "rr_immutable",
        "recommendation_id": "rec_immutable",
        "lifecycle_stage": "recommendation_ready",
        "recommendation": "reject",
        "evidence_refs": ["ev_1"],
    }

    snapshot = json.loads(json.dumps(report))
    decision = run_decision_from_report(report, recommendation)

    assert decision["outcome"] == "rejected"
    assert report == snapshot
