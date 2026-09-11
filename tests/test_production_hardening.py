import json
import shutil
from pathlib import Path

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
            attribute = str(claim.get("attribute", "coverage")).strip() or "coverage"
            value_type = str(value.get("type", "evidence")).strip() or "evidence"
            rendered_sections.append({
                "section_index": item["section_index"],
                "body": (
                    f"This section addresses {attribute} using {value_type} evidence "
                    f"when evaluating {item['heading'].lower()}."
                ),
            })

        return {
            "sections": rendered_sections,
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
            "images": [{
                "image_id": "img_1",
                "section_index": sections[0]["section_index"],
                "placement": "after introduction",
                "prompt": "Professional insurance research editorial illustration, no text.",
                "alt_text": "Insurance research editorial illustration",
                "evidence_refs": sections[0]["evidence_refs"],
            }],
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


def _run_contract(project_name: str) -> dict:
    result = run_production_orchestrator(project_name, llm_provider=FakeWriter(), deliver=False)
    assert result["project_name"] == project_name
    assert result["schema_version"] == "1.0"
    assert result["lifecycle_stage"] == "completed"
    assert result["completed_stages"] == list(STAGES)
    assert result["remaining_stages"] == []
    assert result["error"] is None
    assert result["audit"] == {"method": "irl_production_orchestrator", "version": "v1", "validation_status": "validated"}
    package = result["article_package"]
    assert isinstance(package, dict)
    assert package["production_id"].startswith("production_")
    assert package["lifecycle_stage"] == "production_ready"
    assert package["publication"] == {"mode": "wordpress_draft", "publish": False, "human_approval_required": True}
    assert package["audit"] == {"method": "article_production_contract", "version": "v1", "validation_status": "validated"}
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
    first_a = _run_contract(PROJECT_A)
    first_b = _run_contract(PROJECT_B)
    keyword_a = json.loads((research_root / PROJECT_A / "keyword.json").read_text(encoding="utf-8"))
    keyword_b = json.loads((research_root / PROJECT_B / "keyword.json").read_text(encoding="utf-8"))
    assert keyword_a["keyword"] == keyword_b["keyword"]
    assert first_a["project_name"] != first_b["project_name"]
    assert first_a["orchestration_id"] != first_b["orchestration_id"]
    assert first_a["lineage"].keys() == first_b["lineage"].keys()
    assert first_a["article_package"]["lineage"].keys() == first_b["article_package"]["lineage"].keys()
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
