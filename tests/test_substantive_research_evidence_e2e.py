from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research import agent
from agents.research.article_draft_agent import run as run_article_draft
from agents.research.content_brief_agent import run as run_content_brief
from agents.research.section_evidence_readiness import evaluate_section_readiness
from agents.research.article_draft_agent import _load_evidence_records


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MATERIAL = json.loads(
    (ROOT / "tests/data/substantive-expat-health-insurance-source-material.json").read_text(encoding="utf-8")
)
EVIDENCE_SCHEMA = json.loads(
    (ROOT / "shared/schemas/evidence.schema.json").read_text(encoding="utf-8")
)
EVIDENCE_VALIDATOR = Draft202012Validator(EVIDENCE_SCHEMA)


class RecordingWriter:
    def __init__(self) -> None:
        self.calls = 0

    def write(self, *, sections, editorial_rules):
        self.calls += 1
        return {
            "sections": [
                {
                    "section_index": item["section_index"],
                    "body": (
                        f"This section is written from the assigned source material for "
                        f"{item['heading'].lower()} and does not add unsupported facts."
                    ),
                }
                for item in sections
            ],
            "tables": [
                {
                    "table_id": "table_1",
                    "title": "Evidence-backed comparison",
                    "section_index": sections[0]["section_index"],
                    "columns": ["Criterion", "Assessment"],
                    "rows": [
                        ["Coverage", "Use the assigned evidence"],
                        ["Cost", "Use the assigned evidence"],
                    ],
                    "evidence_refs": sections[0]["evidence_refs"],
                }
            ],
            "images": [
                {
                    "image_id": "img_1",
                    "section_index": 0,
                    "placement": "after introduction",
                    "prompt": "Professional editorial illustration for an international health insurance article, no text.",
                    "alt_text": "International health insurance editorial illustration",
                    "evidence_refs": sections[0]["evidence_refs"],
                }
            ],
        }


def _prepare_project(tmp_path: Path, project: str = "expat-health-insurance") -> Path:
    source = ROOT / "research" / project
    destination = tmp_path / "research" / project
    destination.parent.mkdir(parents=True)
    shutil.copytree(source, destination)
    (destination / "source-material.json").write_text(
        json.dumps(SOURCE_MATERIAL, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return destination


def test_substantive_research_produces_canonical_evidence_and_unblocks_article_writer(tmp_path, monkeypatch):
    root = _prepare_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    report = agent.run("expat-health-insurance")
    assert report is None
    run_content_brief("expat-health-insurance")

    report_data = json.loads((root / "research-report.json").read_text(encoding="utf-8"))
    refs = report_data["evidence_refs"]["substantive"]
    assert refs

    records = _load_evidence_records("expat-health-insurance")
    by_id = {item["evidence_id"]: item for item in records}
    assert set(refs) <= set(by_id)

    for record in (by_id[ref] for ref in refs):
        EVIDENCE_VALIDATOR.validate(record)

    brief = json.loads((root / "content-brief.json").read_text(encoding="utf-8"))
    readiness = evaluate_section_readiness(
        report_id=report_data["report_id"],
        outline=brief["outline"],
        evidence_refs=brief["evidence_refs"],
        evidence_records=records,
    )
    assert [item["readiness"] for item in readiness] == ["READY"] * 7

    writer = RecordingWriter()
    draft = run_article_draft("expat-health-insurance", llm_provider=writer)

    assert writer.calls == 1
    assert draft["lifecycle_stage"] == "draft_ready"
    assert len(draft["sections"]) == 7
    assert all(section["evidence_refs"] for section in draft["sections"])
    assert len(draft["section_evidence_contracts"]) == 7
    assert all(item["status"] == "ready" for item in draft["section_evidence_contracts"])
    assert draft["report_id"] == report_data["report_id"]


def test_substantive_research_blocks_article_when_required_pricing_evidence_is_missing(tmp_path, monkeypatch):
    root = _prepare_project(tmp_path)
    material = json.loads((root / "source-material.json").read_text(encoding="utf-8"))
    for source in material["sources"]:
        source["facts"] = [
            fact
            for fact in source["facts"]
            if not (
                fact["claim_type"] == "pricing_fact"
                and fact["attribute"] == "premium"
            )
        ]
    (root / "source-material.json").write_text(
        json.dumps(material, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    (root / "article-draft.json").unlink()
    agent.run("expat-health-insurance")

    writer = RecordingWriter()
    with pytest.raises(
        ValueError,
        match=r"Costs and Pricing Factors|costs_and_pricing_factors|required_claim_missing",
    ):
        run_article_draft("expat-health-insurance", llm_provider=writer)

    assert writer.calls == 0
    assert not (root / "article-draft.json").exists()


def test_substantive_research_rejects_signal_claims(tmp_path, monkeypatch):
    root = _prepare_project(tmp_path)
    material = json.loads((root / "source-material.json").read_text(encoding="utf-8"))
    material["sources"][0]["facts"].append(
        {
            "claim_type": "query_intent",
            "attribute": "primary_intent",
            "subject": {"type": "keyword", "id": "expat health insurance"},
            "value": {"type": "categorical", "data": "Informational"},
            "confidence": 1.0,
            "relation": "supports",
        }
    )
    (root / "source-material.json").write_text(
        json.dumps(material, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="not allowed by Expected Claim Map"):
        agent.run("expat-health-insurance")
