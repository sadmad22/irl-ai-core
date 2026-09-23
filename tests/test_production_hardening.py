import json
import shutil
from pathlib import Path

from agents.research import article_draft_agent
from agents.research.evidence.domain_common import build_observation
from agents.research import production_orchestrator as orchestrator
from agents.research.final_optimization import build_final_optimization
from agents.research.production_orchestrator import STAGES, run_production_orchestrator

FIXTURE_PROJECT = "expat-health-insurance"
PROJECT_A = "phase8-repeatability-a"
PROJECT_B = "phase8-repeatability-b"


class FakeWriter:
    def write(self, *, sections, editorial_rules):
        rendered_sections = []
        for item in sections:
            record = item["evidence_records"][0]
            claim = record.get("claim") if isinstance(record.get("claim"), dict) else {}
            value = record.get("value") if isinstance(record.get("value"), dict) else {}
            attribute = (str(claim.get("attribute", "coverage")).strip().replace("_", " ")) or "coverage"
            value_type = str(value.get("type", "evidence")).strip() or "evidence"
            rendered_sections.append({"section_index": item["section_index"], "body": f"This section addresses {attribute} using {value_type} evidence when evaluating {item['heading'].lower()}."})
        return {
            "sections": rendered_sections,
            "tables": [{"table_id": "table_1", "title": "Comparison overview", "section_index": sections[0]["section_index"], "columns": ["Criterion", "Assessment"], "rows": [["Coverage", "Compare available coverage options"], ["Cost", "Compare expected premium differences"]], "evidence_refs": sections[0]["evidence_refs"]}],
            "images": [{"image_id": "img_1", "section_index": sections[0]["section_index"], "placement": "after introduction", "prompt": "Professional insurance research editorial illustration, no text.", "alt_text": "Insurance research editorial illustration", "evidence_refs": sections[0]["evidence_refs"]}],
        }


def _prepare_project(source_root: Path, target_root: Path, project_name: str) -> Path:
    source = source_root / "research" / FIXTURE_PROJECT
    target = target_root / "research" / project_name
    shutil.copytree(source, target)
    metadata_path = target / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["project_name"] = project_name
    metadata["id"] = f"rr_{project_name}"
    metadata_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")
    return target


def _install_test_evidence_contract(monkeypatch):
    original = article_draft_agent.run_content_brief_agent

    def wrapped(project_name: str):
        result = original(project_name)
        root = Path("research") / project_name

        captured_at = "2026-08-21T12:45:59Z"
        report_id = str(result["report_id"])
        keyword = str(result["primary_keyword"])

        source_base = {
            "type": "official",
            "provider": "local-test",
            "retrieved_at": captured_at,
        }
        provenance = {
            "analyzer": "production_hardening_fixture",
            "analyzer_version": "1.0",
            "method": "deterministic_test",
        }

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

        refs = list(result.get("evidence_refs", []))
        for index, (domain, claim_type, attribute, data, source_id) in enumerate(required_records, start=1):
            source = dict(source_base)
            source["source_id"] = source_id
            if domain == "intent":
                source["type"] = "query"

            record = build_observation(
                report_id=report_id,
                domain=domain,
                subject={"type": "keyword", "id": keyword},
                claim={"type": claim_type, "attribute": attribute},
                value={"type": "text", "data": data},
                source=source,
                provenance=provenance,
                confidence=1.0,
                captured_at=captured_at,
                evidence_id=f"ev_hardening_{index:02d}_{project_name}",
            )
            (root / f"test-evidence-required-{index:02d}.json").write_text(
                json.dumps(record, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )
            refs.append(record["evidence_id"])

        brief_path = root / "content-brief.json"
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
        brief["evidence_refs"] = list(dict.fromkeys(refs))
        brief_path.write_text(
            json.dumps(brief, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )

        return brief

    monkeypatch.setattr(
        article_draft_agent,
        "run_content_brief_agent",
        wrapped,
    )

def _run_contract(project_name: str) -> dict:
    result = run_production_orchestrator(project_name, llm_provider=FakeWriter(), deliver=False)
    assert result["project_name"] == project_name
    assert result["schema_version"] == "1.0"
    assert result["lifecycle_stage"] == "completed", result["error"]
    expected_completed = [stage for stage in STAGES[:10] if stage in {"research", "intelligence", "configuration", "structure", "draft", "editorial_cleanup", "optimization", "qa"}]
    assert result["completed_stages"] == expected_completed
    assert result["current_stage"] is None
    assert result["remaining_stages"] == []
    assert result["error"] is None
    assert result["audit"] == {"method": "irl_production_orchestrator", "version": "v1", "validation_status": "validated"}
    assert "production" in result
    assert set(result["production"]) == {"assembly", "package", "boundary", "wordpress"}
    return result


def test_production_repeatability_across_two_isolated_projects(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    source = repo_root / "research" / FIXTURE_PROJECT
    assert source.is_dir()
    research_root = tmp_path / "research"
    research_root.mkdir()
    _prepare_project(repo_root, tmp_path, PROJECT_A)
    _prepare_project(repo_root, tmp_path, PROJECT_B)
    monkeypatch.chdir(tmp_path)
    _install_test_evidence_contract(monkeypatch)

    original_pipeline = orchestrator.run_content_research_to_wordpress_draft

    def pipeline_with_final_optimization(project_name, **kwargs):
        result = original_pipeline(project_name, **kwargs)
        article = result["article_draft"]
        result["final_optimization"] = build_final_optimization(
            report={"report_id": article["report_id"]},
            decision={"decision_id": article["decision_id"]},
            strategy={"strategy_id": article["strategy_id"]},
            brief={"brief_id": article["brief_id"]},
            final_values={
                "seo_title": "Expat Health Insurance",
                "meta_description": "Compare expat health insurance coverage and costs.",
                "primary_keyword": "expat health insurance",
                "slug": "expat-health-insurance",
            },
        )
        return result

    monkeypatch.setattr(orchestrator, "run_content_research_to_wordpress_draft", pipeline_with_final_optimization)

    first_a = _run_contract(PROJECT_A)
    first_b = _run_contract(PROJECT_B)
    keyword_a = json.loads((research_root / PROJECT_A / "keyword.json").read_text(encoding="utf-8"))
    keyword_b = json.loads((research_root / PROJECT_B / "keyword.json").read_text(encoding="utf-8"))
    assert keyword_a["keyword"] == keyword_b["keyword"]
    assert first_a["project_name"] != first_b["project_name"]
    assert first_a["orchestration_id"] != first_b["orchestration_id"]
    assert first_a["lineage"].keys() == first_b["lineage"].keys()
    metadata_a = json.loads((research_root / PROJECT_A / "metadata.json").read_text(encoding="utf-8"))
    metadata_b = json.loads((research_root / PROJECT_B / "metadata.json").read_text(encoding="utf-8"))
    assert metadata_a["project_name"] == PROJECT_A
    assert metadata_b["project_name"] == PROJECT_B
    assert metadata_a["id"] != metadata_b["id"]
    second_a = _run_contract(PROJECT_A)
    second_b = _run_contract(PROJECT_B)
    assert second_a == first_a
    assert second_b == first_b
    for project_name in (PROJECT_A, PROJECT_B):
        metadata = json.loads((research_root / project_name / "metadata.json").read_text(encoding="utf-8"))
        assert metadata["project_name"] == project_name
        assert metadata["status"] == "wordpress_draft_ready"
