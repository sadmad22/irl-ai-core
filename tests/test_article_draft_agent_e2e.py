from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.research import article_draft_agent
from agents.research.article_draft_agent import run


class FakeWriter:
    def write(self, *, sections, editorial_rules):
        return {
            "sections": [
                {"section_index": item["section_index"], "body": f"Readers can evaluate {item['heading'].lower()} using the available evidence and the criteria described in the brief."}
                for item in sections
            ],
            "tables": [
                {
                    "table_id": "table_1",
                    "title": "Comparison overview",
                    "section_index": sections[0]["section_index"],
                    "columns": ["Criterion", "Assessment"],
                    "rows": [
                        ["Coverage", "Compare available coverage options"],
                        ["Cost", "Compare expected premium differences"],
                    ],
                    "evidence_refs": sections[0]["evidence_refs"],
                }
            ],
            "images": [
                {
                    "image_id": "img_1",
                    "section_index": 0,
                    "placement": "after introduction",
                    "prompt": "Professional editorial illustration for an insurance research article, no text.",
                    "alt_text": "Insurance research editorial illustration",
                    "evidence_refs": sections[0]["evidence_refs"],
                }
            ],
        }


def _seed(tmp_path: Path, project: str = "draft-demo") -> Path:
    root = tmp_path / "research" / project
    root.mkdir(parents=True)
    (root / "keyword.json").write_text(
        json.dumps({"keyword": "best expat health insurance", "language": "en", "country": "US"}),
        encoding="utf-8",
    )
    (root / "metadata.json").write_text(
        json.dumps({"id": "rr_draft_demo", "project_name": project}), encoding="utf-8"
    )
    (root / "search-metrics.json").write_text(
        json.dumps({"search_volume": 1000, "competition": 0.2, "cpc": 2.5}),
        encoding="utf-8",
    )
    (root / "serp-analysis.json").write_text(
        json.dumps({
            "keyword": "best expat health insurance",
            "results": [
                {"position": 1, "domain": "example.com", "title": "Best Expat Health Insurance", "url": "https://example.com/guide"},
                {"position": 2, "domain": "example.org", "title": "Expat Health Insurance Plans", "url": "https://example.org/plans"},
            ],
        }),
        encoding="utf-8",
    )
    required_records = [
        ("topic", "topic_definition", "definition", "Expat health insurance is international health coverage for people living abroad.", "source:official-definition"),
        ("intent", "query_intent", "primary_intent", "Informational", "source:query"),
        ("topic", "topic_scope", "scope", "Coverage scope depends on the plan and destination.", "source:official-scope"),
        ("eligibility", "eligibility", "who_needs_it", "People living abroad can evaluate this type of coverage.", "source:official-eligibility"),
        ("use_case", "use_case", "primary_use", "The primary use is to address health coverage needs while living abroad.", "source:official-use"),
        ("coverage", "coverage_fact", "coverage", "Plans provide defined healthcare coverage according to their terms.", "source:official-coverage"),
        ("coverage", "coverage_fact", "benefit", "A plan may provide stated healthcare benefits under its terms.", "source:official-benefit"),
        ("coverage", "exclusion_fact", "exclusion", "Plan exclusions define circumstances not covered under the terms.", "source:official-exclusion"),
        ("market", "pricing_fact", "premium", "Annual premium is a concrete pricing fact for the evaluated plan.", "source:official-premium"),
        ("market", "pricing_factor", "cost_driver", "Coverage level is a cost driver that can affect pricing.", "source:official-cost-driver"),
        ("market", "pricing_factor", "price_variable", "Deductible level is a price variable.", "source:official-price-variable"),
        ("comparison", "comparison_fact", "criterion", "Coverage, cost, and network are comparison criteria.", "source:official-criterion"),
        ("comparison", "option_attribute", "coverage_difference", "Options can differ in the coverage they provide.", "source:official-coverage-difference"),
        ("comparison", "option_attribute", "cost_difference", "Options can differ in cost based on their terms.", "source:official-cost-difference"),
        ("question", "question_fact", "question", "Readers may ask what expat health insurance covers.", "source:official-question"),
        ("answer", "answer_fact", "answer", "The answer should describe the applicable coverage terms from the source.", "source:official-answer"),
        ("source", "source_identity", "source", "The article uses identified research sources.", "source:official-source"),
        ("provenance", "provenance_fact", "method", "Evidence is produced through a documented deterministic method.", "source:official-method"),
        ("evidence", "lineage_fact", "evidence_lineage", "Evidence retains traceable lineage to the research record.", "source:official-lineage"),
    ]

    for index, (domain, claim_type, attribute, data, source_id) in enumerate(required_records, start=1):
        record = {
            "evidence_id": f"ev_test_required_{index}",
            "report_id": "rr_draft_demo",
            "schema_version": "1.0",
            "type": "observation",
            "domain": domain,
            "subject": {"type": "keyword", "id": "best expat health insurance"},
            "claim": {"type": claim_type, "attribute": attribute},
            "value": {"type": "text", "data": data},
            "source": {
                "type": "official" if domain != "intent" else "query",
                "source_id": source_id,
                "provider": "test",
                "retrieved_at": "2026-09-23T12:00:00Z",
            },
            "provenance": {
                "analyzer": "e2e_test",
                "analyzer_version": "1.0",
                "method": "deterministic_test",
            },
            "confidence": 1.0,
            "relation": "supports",
            "derived_from": [],
            "captured_at": "2026-09-23T12:00:00Z",
            "status": "active",
        }
        (root / f"evidence-required-{index}.json").write_text(
            json.dumps(record, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
    return root



def _inject_test_evidence_into_brief(monkeypatch, root: Path):
    original = article_draft_agent.run_content_brief_agent

    def wrapped(project_name: str):
        result = original(project_name)
        brief_path = root / "content-brief.json"
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
        refs = list(brief.get("evidence_refs", []))
        for evidence_id in (
            "ev_test_coverage_options",
            "ev_test_cost_premium",
            *[f"ev_test_required_{index}" for index in range(1, 20)],
        ):
            if evidence_id not in refs:
                refs.append(evidence_id)
        brief["evidence_refs"] = refs
        brief_path.write_text(
            json.dumps(brief, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
        return brief

    monkeypatch.setattr(article_draft_agent, "run_content_brief_agent", wrapped)


def test_writer_agent_runs_full_downstream_path(tmp_path, monkeypatch):
    root = _seed(tmp_path)
    monkeypatch.chdir(tmp_path)
    _inject_test_evidence_into_brief(monkeypatch, root)

    draft = run("draft-demo", llm_provider=FakeWriter())

    report = json.loads((root / "research-report.json").read_text())
    decision = json.loads((root / "decision.json").read_text())
    strategy = json.loads((root / "content-strategy.json").read_text())
    brief = json.loads((root / "content-brief.json").read_text())
    saved = json.loads((root / "article-draft.json").read_text())
    metadata = json.loads((root / "metadata.json").read_text())

    assert draft == saved
    assert decision["outcome"] == "approved"
    assert brief["lifecycle_stage"] == "content_brief_ready"
    assert saved["lifecycle_stage"] == "draft_ready"
    assert saved["schema_version"] == "1.1"
    assert saved["brief_id"] == brief["brief_id"]
    assert saved["strategy_id"] == strategy["strategy_id"]
    assert saved["decision_id"] == decision["decision_id"]
    assert saved["report_id"] == report["report_id"]
    assert saved["evidence_refs"] == brief["evidence_refs"]
    assert saved["images"]
    assert metadata["status"] == "draft_ready"


def test_writer_agent_is_deterministic_and_does_not_mutate_upstream(tmp_path, monkeypatch):
    root = _seed(tmp_path, "stable-draft")
    monkeypatch.chdir(tmp_path)
    _inject_test_evidence_into_brief(monkeypatch, root)

    first = run("stable-draft", llm_provider=FakeWriter())
    upstream_first = {
        name: (root / name).read_text()
        for name in [
            "research-report.json",
            "recommendation.json",
            "decision.json",
            "content-strategy.json",
            "content-brief.json",
        ]
    }

    second = run("stable-draft", llm_provider=FakeWriter())
    upstream_second = {
        name: (root / name).read_text()
        for name in upstream_first
    }

    assert first == second
    assert first["draft_id"] == second["draft_id"]
    assert upstream_first == upstream_second


def test_writer_agent_requires_a_publishable_content_brief(tmp_path, monkeypatch):
    root = _seed(tmp_path, "guarded-draft")
    monkeypatch.chdir(tmp_path)

    (root / "content-brief.json").write_text(
        json.dumps({
            "brief_id": "brief_guard",
            "report_id": "rr_guard",
            "decision_id": "dec_guard",
            "strategy_id": "strat_guard",
            "lifecycle_stage": "draft_ready",
            "evidence_refs": ["ev_guard"],
            "outline": [{"heading": "Intro", "purpose": "Introduce the topic"}],
            "content_type": "guide",
            "primary_keyword": "guarded keyword",
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="content_brief_ready"):
        from agents.research.article_draft import build_article_draft
        build_article_draft(content_brief=json.loads((root / "content-brief.json").read_text()), llm_provider=FakeWriter())


def test_e2e_gate_preserves_lineage_sections_and_claim_grounding(tmp_path, monkeypatch):
    root = _seed(tmp_path, "gate-regression")
    monkeypatch.chdir(tmp_path)
    _inject_test_evidence_into_brief(monkeypatch, root)

    original_build = article_draft_agent.build_article_draft
    pre_gate = {}

    def wrapped_build(*, content_brief, evidence_records=None, editorial_evidence=None, llm_provider):
        pre_gate["brief"] = {
            key: json.loads(json.dumps(content_brief[key]))
            for key in ("brief_id", "report_id", "decision_id", "strategy_id", "evidence_refs", "outline")
        }
        return original_build(
            content_brief=content_brief,
            evidence_records=evidence_records,
            editorial_evidence=editorial_evidence,
            llm_provider=llm_provider,
        )

    monkeypatch.setattr(article_draft_agent, "build_article_draft", wrapped_build)

    draft = run("gate-regression", llm_provider=FakeWriter())

    assert pre_gate["brief"]["brief_id"] == draft["brief_id"]
    assert pre_gate["brief"]["report_id"] == draft["report_id"]
    assert pre_gate["brief"]["decision_id"] == draft["decision_id"]
    assert pre_gate["brief"]["strategy_id"] == draft["strategy_id"]
    assert draft["evidence_refs"] == pre_gate["brief"]["evidence_refs"]

    expected_sections = [
        (index, item["heading"], item["purpose"])
        for index, item in enumerate(pre_gate["brief"]["outline"], start=1)
    ]
    actual_sections = [
        (index, section["heading"], section["purpose"])
        for index, section in enumerate(draft["sections"], start=1)
    ]
    assert actual_sections == expected_sections

    contracts = draft["section_evidence_contracts"]
    assert len(contracts) == len(expected_sections)
    for contract, (index, heading, _) in zip(contracts, expected_sections):
        assert contract["section_index"] == index
        assert contract["heading"] == heading
        assert contract["status"] == "ready"
        assert contract["evidence_refs"]

    top_level_refs = set(draft["evidence_refs"])
    claims = [claim for section in draft["sections"] for claim in section["claims"]]
    claim_ids = [claim["claim_id"] for claim in claims]
    assert len(claim_ids) == len(set(claim_ids))

    for section, contract in zip(draft["sections"], contracts):
        section_refs = set(section["evidence_refs"])
        assert section_refs == set(contract["evidence_refs"])
        assert section_refs <= top_level_refs
        assert section["claims"]
        for claim in section["claims"]:
            assert claim["grounding_status"] in {"grounded", "blocked"}
            if claim["grounding_status"] == "grounded":
                assert claim["evidence_refs"]
                assert set(claim["evidence_refs"]) <= section_refs
            else:
                assert claim["evidence_refs"] == []


def test_e2e_gate_blocks_superficially_complete_article_without_substantive_evidence(tmp_path, monkeypatch):
    root = _seed(tmp_path, "gate-blocked")
    monkeypatch.chdir(tmp_path)
    _inject_test_evidence_into_brief(monkeypatch, root)

    # Keep the brief lineage and surface signals intact, but remove the
    # substantive premium evidence required by the Costs section.
    (root / "evidence-required-9.json").unlink()

    class TrackingWriter(FakeWriter):
        calls = 0

        def write(self, *, sections, editorial_rules):
            self.calls += 1
            return super().write(sections=sections, editorial_rules=editorial_rules)

    writer = TrackingWriter()

    with pytest.raises(ValueError, match="Section Evidence Quality Gate blocked Article Writer"):
        run("gate-blocked", llm_provider=writer)

    assert writer.calls == 0
    assert not (root / "article-draft.json").exists()

    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["status"] != "draft_ready"
