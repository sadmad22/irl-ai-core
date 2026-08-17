import json
import shutil
from pathlib import Path

from jsonschema import Draft202012Validator

from agents.research import agent

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "shared/schemas/research-report-assembly.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def test_research_agent_builds_canonical_report_end_to_end(tmp_path, monkeypatch):
    project_name = "expat-health-insurance"
    source = ROOT / "research" / project_name
    destination = tmp_path / "research" / project_name
    destination.parent.mkdir(parents=True)
    shutil.copytree(source, destination)

    monkeypatch.chdir(tmp_path)
    agent.run(project_name)

    report_path = destination / "research-report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))

    VALIDATOR.validate(report)
    assert report["report_id"] == f"rr_{project_name}"
    assert report["keyword"]["keyword"] == "expat health insurance"
    assert report["search_intent"]
    assert report["serp_analysis"]
    assert report["competitor_analysis"] is not None
    assert report["entity_analysis"]["entities"]
    assert report["question_analysis"]
    assert report["business_analysis"]["commercial_value"] in {"low", "medium", "high"}
    assert 0 <= report["topical_authority"]["authority_score"] <= 1
    assert report["evidence_refs"]["intent"]
    assert report["evidence_refs"]["entity"]
    assert report["evidence_refs"]["question"]
    assert report["evidence_refs"]["business"]
    assert report["evidence_refs"]["authority"]
    assert report["recommendation"] is None
    assert report["decision"] is None
    assert report["audit"]["validation_status"] == "pending"

    for filename in (
        "entity-analysis.json",
        "entity-evidence.json",
        "question-analysis.json",
        "question-evidence.json",
        "business-analysis.json",
        "business-evidence.json",
        "authority-analysis.json",
        "authority-evidence.json",
    ):
        assert (destination / filename).exists()


def test_research_agent_report_is_stable_on_second_run(tmp_path, monkeypatch):
    project_name = "expat-health-insurance"
    source = ROOT / "research" / project_name
    destination = tmp_path / "research" / project_name
    destination.parent.mkdir(parents=True)
    shutil.copytree(source, destination)

    monkeypatch.chdir(tmp_path)
    agent.run(project_name)
    first = json.loads((destination / "research-report.json").read_text(encoding="utf-8"))

    agent.run(project_name)
    second = json.loads((destination / "research-report.json").read_text(encoding="utf-8"))

    assert first == second
