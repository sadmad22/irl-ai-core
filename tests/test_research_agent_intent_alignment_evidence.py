import json
from pathlib import Path

import agents.research.agent as research_agent


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_research_agent_writes_full_intent_evidence_lineage_end_to_end(tmp_path, monkeypatch):
    project_name = "alignment-project"
    project_dir = tmp_path / "research" / project_name

    _write_json(
        project_dir / "keyword.json",
        {
            "keyword": "expat health insurance",
            "language": "en",
            "country": "US",
        },
    )
    _write_json(
        project_dir / "metadata.json",
        {
            "id": "rr_alignment_001",
            "status": "draft",
            "project_name": project_name,
        },
    )
    _write_json(project_dir / "search-metrics.json", {})
    _write_json(
        project_dir / "serp-analysis.json",
        {
            "keyword": "expat health insurance",
            "language": "en",
            "country": "US",
            "results": [
                {
                    "position": 1,
                    "domain": "example.com",
                    "title": "Expat Health Insurance Guide",
                    "url": "https://example.com/guide?utm_source=test",
                },
                {
                    "position": 2,
                    "domain": "example.org",
                    "title": "Expat Health Insurance Plans",
                    "url": "https://example.org/plans?utm_medium=test",
                },
                {
                    "position": 3,
                    "domain": "example.net",
                    "title": "How Expat Health Insurance Works",
                    "url": "https://example.net/how-it-works",
                },
            ],
        },
    )

    monkeypatch.chdir(tmp_path)
    research_agent.run(project_name)

    query_evidence = json.loads(
        (project_dir / "query-intent-evidence.json").read_text(encoding="utf-8")
    )
    serp_evidence = json.loads(
        (project_dir / "serp-intent-evidence.json").read_text(encoding="utf-8")
    )
    alignment_evidence = json.loads(
        (project_dir / "intent-alignment-evidence.json").read_text(encoding="utf-8")
    )

    assert query_evidence["report_id"] == "rr_alignment_001"
    assert serp_evidence
    assert alignment_evidence["report_id"] == "rr_alignment_001"
    assert alignment_evidence["type"] == "derived"
    assert alignment_evidence["claim"] == {
        "type": "intent_alignment",
        "attribute": "alignment",
    }

    canonical_serp_ids = {
        item["evidence_id"]
        for item in serp_evidence
        if item["claim"]["attribute"] in {"dominant_intent", "mixed_intent"}
    }
    lineage = set(alignment_evidence["derived_from"])

    assert query_evidence["evidence_id"] in lineage
    assert canonical_serp_ids.issubset(lineage)
    assert not lineage.intersection(
        {
            item["evidence_id"]
            for item in serp_evidence
            if item["type"] == "observation"
        }
    )
    assert alignment_evidence["provenance"]["analyzer"] == "intent_alignment"


def test_research_agent_alignment_evidence_has_stable_lineage(tmp_path, monkeypatch):
    project_name = "stable-alignment-project"
    project_dir = tmp_path / "research" / project_name

    _write_json(
        project_dir / "keyword.json",
        {"keyword": "consultant insurance", "language": "en", "country": "US"},
    )
    _write_json(
        project_dir / "metadata.json",
        {"id": "rr_stable_alignment", "status": "draft", "project_name": project_name},
    )
    _write_json(project_dir / "search-metrics.json", {})
    _write_json(project_dir / "serp-analysis.json", {"keyword": "consultant insurance", "language": "en", "country": "US", "results": [{"position": 1, "domain": "example.com", "title": "Consultant Insurance Guide", "url": "https://example.com/guide"}]})

    monkeypatch.chdir(tmp_path)
    research_agent.run(project_name)

    first = json.loads((project_dir / "intent-alignment-evidence.json").read_text(encoding="utf-8"))
    first_query = json.loads((project_dir / "query-intent-evidence.json").read_text(encoding="utf-8"))

    research_agent.run(project_name)

    second = json.loads((project_dir / "intent-alignment-evidence.json").read_text(encoding="utf-8"))
    second_query = json.loads((project_dir / "query-intent-evidence.json").read_text(encoding="utf-8"))

    assert first["evidence_id"] == second["evidence_id"]
    assert first["derived_from"] == second["derived_from"]
    assert first["report_id"] == second["report_id"]
    assert first_query["evidence_id"] == second_query["evidence_id"]
