import importlib.util
import json
from pathlib import Path

import pytest

from agents.research.evidence.serp_strategy_signal import (
    build_serp_strategy_signal_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "shared" / "schemas" / "evidence.schema.json"


@pytest.fixture
def schema():
    jsonschema = pytest.importorskip("jsonschema")
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8")), jsonschema


def _analysis(strategy_signal="mixed", confidence=0.82):
    return {
        "keyword": "expat health insurance",
        "primary_intent": "Informational",
        "dominant_serp_intent": "Informational",
        "alignment": "mixed",
        "strategy_signal": strategy_signal,
        "confidence": confidence,
    }


def test_builds_strategy_signal_evidence(schema):
    schema_data, jsonschema = schema
    evidence = build_serp_strategy_signal_evidence(
        _analysis(),
        report_id="rr_demo_001",
        intent_alignment_evidence_id="ev_alignment_001",
        captured_at="2026-08-17T12:00:00Z",
    )

    jsonschema.Draft202012Validator(schema_data).validate(evidence)

    assert evidence["type"] == "derived"
    assert evidence["domain"] == "serp"
    assert evidence["claim"] == {
        "type": "serp_strategy_signal",
        "attribute": "strategy_signal",
    }
    assert evidence["value"]["data"] == "mixed"
    assert evidence["derived_from"] == ["ev_alignment_001"]
    assert evidence["provenance"]["analyzer"] == "serp_strategy_signal"
    assert evidence["confidence"] == 0.82


def test_lineage_is_stable_and_scoped_to_report():
    first = build_serp_strategy_signal_evidence(
        _analysis("informational", 1.0),
        report_id="rr_demo_001",
        intent_alignment_evidence_id="ev_alignment_001",
        captured_at="2026-08-17T12:00:00Z",
    )
    second = build_serp_strategy_signal_evidence(
        _analysis("informational", 1.0),
        report_id="rr_demo_001",
        intent_alignment_evidence_id="ev_alignment_001",
        captured_at="2026-08-18T12:00:00Z",
    )
    other_report = build_serp_strategy_signal_evidence(
        _analysis("informational", 1.0),
        report_id="rr_demo_002",
        intent_alignment_evidence_id="ev_alignment_001",
        captured_at="2026-08-17T12:00:00Z",
    )

    assert first["evidence_id"] == second["evidence_id"]
    assert first["evidence_id"] != other_report["evidence_id"]
    assert first["derived_from"] == ["ev_alignment_001"]


def test_supports_all_strategy_signal_values(schema):
    schema_data, jsonschema = schema
    for signal in (
        "informational",
        "commercial",
        "transactional",
        "navigational",
        "mixed",
        "indeterminate",
    ):
        evidence = build_serp_strategy_signal_evidence(
            _analysis(signal),
            report_id="rr_demo_001",
            intent_alignment_evidence_id="ev_alignment_001",
        )
        jsonschema.Draft202012Validator(schema_data).validate(evidence)
        assert evidence["value"]["data"] == signal


def test_rejects_unknown_strategy_signal():
    with pytest.raises(ValueError, match="strategy_signal is invalid"):
        build_serp_strategy_signal_evidence(
            _analysis("unknown"),
            report_id="rr_demo_001",
            intent_alignment_evidence_id="ev_alignment_001",
        )


def test_rejects_invalid_confidence():
    with pytest.raises(ValueError, match="between 0 and 1"):
        build_serp_strategy_signal_evidence(
            _analysis("mixed", 1.1),
            report_id="rr_demo_001",
            intent_alignment_evidence_id="ev_alignment_001",
        )


def test_rejects_missing_alignment_lineage():
    with pytest.raises(ValueError, match="intent_alignment_evidence_id is required"):
        build_serp_strategy_signal_evidence(
            _analysis(),
            report_id="rr_demo_001",
            intent_alignment_evidence_id="",
        )
