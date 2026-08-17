import json
from pathlib import Path

import jsonschema
import pytest

from agents.research.decision import build_decision


SCHEMA = json.loads(Path("shared/schemas/decision.schema.json").read_text(encoding="utf-8"))


def _report():
    return {"report_id": "rr_001", "lifecycle_stage": "research_complete"}


def _recommendation(value="pursue"):
    return {
        "recommendation_id": "rec_001",
        "report_id": "rr_001",
        "lifecycle_stage": "recommendation_ready",
        "recommendation": value,
        "evidence_refs": ["ev_intent", "ev_business"],
    }


def test_decision_follows_pursue_without_re_evaluating_evidence():
    result = build_decision(research_report=_report(), recommendation=_recommendation("pursue"))
    jsonschema.validate(result, SCHEMA)
    assert result["outcome"] == "approved"
    assert result["recommendation_ref"] == "rec_001"
    assert result["evidence_refs"] == ["ev_intent", "ev_business"]


def test_decision_maps_all_recommendation_states():
    assert build_decision(research_report=_report(), recommendation=_recommendation("pursue"))["outcome"] == "approved"
    assert build_decision(research_report=_report(), recommendation=_recommendation("defer"))["outcome"] == "deferred"
    assert build_decision(research_report=_report(), recommendation=_recommendation("reject"))["outcome"] == "rejected"


def test_decision_is_deterministic():
    first = build_decision(research_report=_report(), recommendation=_recommendation())
    second = build_decision(research_report=_report(), recommendation=_recommendation())
    assert first == second


def test_decision_requires_recommendation_ready():
    rec = _recommendation()
    rec["lifecycle_stage"] = "research_complete"
    with pytest.raises(ValueError, match="recommendation_ready"):
        build_decision(research_report=_report(), recommendation=rec)


def test_decision_requires_matching_report():
    rec = _recommendation()
    rec["report_id"] = "rr_other"
    with pytest.raises(ValueError, match="must match"):
        build_decision(research_report=_report(), recommendation=rec)


def test_decision_requires_explicit_evidence_lineage():
    rec = _recommendation()
    rec["evidence_refs"] = []
    with pytest.raises(ValueError, match="evidence_refs"):
        build_decision(research_report=_report(), recommendation=rec)


def test_decision_rejects_unknown_recommendation():
    with pytest.raises(ValueError, match="pursue, defer, or reject"):
        build_decision(research_report=_report(), recommendation=_recommendation("maybe"))


def test_decision_requires_research_complete():
    report = _report()
    report["lifecycle_stage"] = "recommendation_ready"
    with pytest.raises(ValueError, match="research_complete"):
        build_decision(research_report=report, recommendation=_recommendation())
