from __future__ import annotations

import copy

import pytest

from agents.research import controlled_production
from agents.research import production_orchestrator as orchestrator
from agents.research.production_assembly_engine import ProductionAssemblyEngineError, build_production_assembly

LINEAGE = {"report_id": "report_123", "decision_id": "decision_123", "strategy_id": "strategy_123", "brief_id": "brief_123", "draft_id": "draft_123", "quality_id": "quality_123"}
INTENT = {"target": "wordpress", "mode": "wordpress_draft", "publish": False, "human_approval_required": True}
OPTIMIZATION = {"optimization_id": "optimization_123", "schema_version": "1.0", "method_version": "v1", "lifecycle_stage": "optimization_ready", "seo_title": "Expat Health Insurance Guide", "meta_description": "A practical guide to expat health insurance.", "primary_keyword": "expat health insurance", "slug": "expat-health-insurance-guide", "lineage": {k: LINEAGE[k] for k in ("report_id", "decision_id", "strategy_id", "brief_id")}}


def _artifacts() -> dict:
    return {
        "article_draft": {**LINEAGE, "lifecycle_stage": "draft_ready", "content_type": "guide", "title": "Expat Health Insurance Guide", "slug": "expat-health-insurance-guide", "sections": [{"section_id": "section_0", "heading": "Overview", "body": "Evidence-backed article text.", "purpose": "Explain the topic", "evidence_refs": ["evidence_1"], "claims": [{"claim_id": "claim_1", "text": "Evidence-backed article text.", "evidence_refs": ["evidence_1"], "grounding_status": "grounded"}]}], "tables": []},
        "quality": {**LINEAGE, "lifecycle_stage": "article_draft_quality_ready", "outcome": "passed", "audit": {"validation_status": "validated"}},
        "claim_audit": {"outcome": "passed", "audit": {"validation_status": "validated"}},
        "editorial_review": {"outcome": "approved", "audit": {"validation_status": "validated"}},
        "optimization": copy.deepcopy(OPTIMIZATION),
        "media": {"images": [{"image_id": "image_1", "section_index": 0, "placement": "hero", "prompt": "Editorial insurance illustration", "alt_text": "Expat health insurance illustration", "materialization_status": "materialized", "asset_ref": "media_1"}]},
        "linking": {"internal": [{"link_id": "link_1", "section_index": 0, "target_url": "https://insurancereviewlab.com/insurance/", "anchor_text": "insurance coverage", "placement": "body"}], "external": []},
        "taxonomy": {"categories": ["Expat Insurance"], "tags": ["health insurance"]},
        "production_intent": copy.deepcopy(INTENT),
        "lineage": copy.deepcopy(LINEAGE) | {"optimization_id": "optimization_123"},
    }


def _early() -> dict:
    a = _artifacts()
    return {"research_report": {}, "content_brief": {}, "article_draft": copy.deepcopy(a["article_draft"]), "article_draft_quality": copy.deepcopy(a["quality"]), "editorial_review": copy.deepcopy(a["editorial_review"]), "media": copy.deepcopy(a["media"]), "linking": copy.deepcopy(a["linking"]), "final_optimization": copy.deepcopy(OPTIMIZATION), "claim_audit": copy.deepcopy(a["claim_audit"]), "seo_validation": {}, "publication": {"gate_status": "allowed"}}


def _canonical_orchestration(*, live: bool = False) -> tuple[dict, dict]:
    captured = {"assembly": None, "package": None, "boundary": None, "wordpress": None}
    original_assembly = orchestrator.build_production_assembly
    original_package = orchestrator.build_article_package
    original_boundary = orchestrator.build_production_delivery_boundary
    original_wordpress = orchestrator.deliver_wordpress_delivery_boundary

    def capture_assembly(**kwargs):
        value = original_assembly(**kwargs); captured["assembly"] = value; return value

    def capture_package(**kwargs):
        value = original_package(**kwargs); captured["package"] = value; return value

    def capture_boundary(**kwargs):
        value = original_boundary(**kwargs); captured["boundary"] = value; return value

    def capture_wordpress(**kwargs):
        captured["wordpress"] = kwargs["boundary"]
        return {"execution_mode": "live", "response": {"platform_post_id": 123, "remote_status": "draft", "edit_url": "https://example.test/wp-admin/post.php?post=123&action=edit"}}

    orchestrator.build_production_assembly = capture_assembly
    orchestrator.build_article_package = capture_package
    orchestrator.build_production_delivery_boundary = capture_boundary
    if live:
        orchestrator.deliver_wordpress_delivery_boundary = capture_wordpress
    try:
        result = orchestrator.build_production_orchestration(project_name="expat-health-insurance", result=_early() | _artifacts(), deliver=True, delivery_mode="live" if live else "dry_run")
    finally:
        orchestrator.build_production_assembly = original_assembly
        orchestrator.build_article_package = original_package
        orchestrator.build_production_delivery_boundary = original_boundary
        orchestrator.deliver_wordpress_delivery_boundary = original_wordpress
    return result, captured


def _run_ready() -> dict:
    run = controlled_production.create_controlled_production_run(project_name="expat-health-insurance", production_id="production_0123456789abcdef", orchestration_id="orchestration_0123456789abcdef")
    run = controlled_production.transition_controlled_production_run(run, status="running")
    run["production_checkpoints"] = {"assembly_id": "assembly_0123456789abcdef", "package_id": "package_0123456789abcdef", "delivery_id": "delivery_0123456789abcdef"}
    return controlled_production.transition_controlled_production_run(run, status="ready_for_delivery")


def test_o7_g01_g02_exact_fourteen_stage_order():
    assert orchestrator.STAGES == ("research", "intelligence", "configuration", "structure", "draft", "editorial_cleanup", "media", "linking", "optimization", "qa", "production_assembly", "article_package", "production_delivery_boundary", "wordpress_delivery")


def test_o7_g01_g02_canonical_optimization_reaches_assembly():
    _, captured = _canonical_orchestration()
    assert captured["assembly"]["artifacts"]["optimization"] == OPTIMIZATION


def test_o7_g01_g02_seo_validation_cannot_replace_optimization():
    source = _artifacts(); source.pop("optimization")
    source["seo_validation"] = {"seo_title": "Wrong", "meta_description": "Wrong"}
    with pytest.raises((ProductionAssemblyEngineError, ValueError)):
        build_production_assembly(project_name="expat-health-insurance", artifacts=source)


def test_o7_g01_g02_first_four_lineage_match_assembly():
    _, captured = _canonical_orchestration()
    assert {k: captured["assembly"]["lineage"][k] for k in ("report_id", "decision_id", "strategy_id", "brief_id")} == {k: LINEAGE[k] for k in ("report_id", "decision_id", "strategy_id", "brief_id")}


def test_o7_g01_g02_optimization_id_survives_assembly():
    _, captured = _canonical_orchestration()
    assert captured["assembly"]["lineage"]["optimization_id"] == "optimization_123"


def test_o7_g01_g02_six_id_lineage_survives_package():
    _, captured = _canonical_orchestration()
    assert {k: captured["package"]["lineage"][k] for k in LINEAGE} == LINEAGE


def test_o7_g01_g02_optimization_id_survives_package():
    _, captured = _canonical_orchestration()
    assert captured["package"]["lineage"]["optimization_id"] == "optimization_123"


def test_o7_g01_g02_package_optimization_values_are_canonical():
    _, captured = _canonical_orchestration()
    assert captured["package"]["optimization"]["seo_title"] == OPTIMIZATION["seo_title"]
    assert captured["package"]["optimization"]["meta_description"] == OPTIMIZATION["meta_description"]


def test_o7_g01_g02_o7_checkpoint_chain_is_valid():
    orchestration, _ = _canonical_orchestration()
    run = controlled_production.create_controlled_production_run(project_name="expat-health-insurance", production_id="production_0123456789abcdef", orchestration_id=orchestration["orchestration_id"])
    run = controlled_production.transition_controlled_production_run(run, status="running")
    run["production_checkpoints"] = {"assembly_id": orchestration["production"]["assembly"]["assembly_id"], "package_id": orchestration["production"]["package"]["package_id"], "delivery_id": orchestration["production"]["boundary"]["delivery_id"]}
    run = controlled_production.transition_controlled_production_run(run, status="ready_for_delivery")
    assert run["production_checkpoints"]["assembly_id"] == orchestration["production"]["assembly"]["assembly_id"]
    assert run["production_checkpoints"]["package_id"] == orchestration["production"]["package"]["package_id"]
    assert run["production_checkpoints"]["delivery_id"] == orchestration["production"]["boundary"]["delivery_id"]


def test_o7_g01_g02_o7_preserves_orchestration_identity():
    orchestration, _ = _canonical_orchestration()
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(controlled_production, "run_production_orchestrator", lambda *a, **k: orchestration)
        run = controlled_production.run_controlled_production("expat-health-insurance", llm_provider=object(), deliver=False)
    finally:
        monkeypatch.undo()
    assert run["orchestration_id"] == orchestration["orchestration_id"]


def test_o7_g01_g02_dry_run_reaches_delivery_readiness_without_wordpress():
    result, captured = _canonical_orchestration()
    assert result["production"]["wordpress"]["execution_mode"] == "dry_run"
    assert result["production"]["wordpress"]["delivery_status"] == "ready"
    assert result["production"]["wordpress"].get("platform_post_id") is None
    assert captured["wordpress"] is None


def test_o7_g01_g02_controlled_delivery_creates_draft_only():
    orchestration, captured = _canonical_orchestration(live=True)
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(controlled_production, "run_production_orchestrator", lambda *a, **k: orchestration)
        run = controlled_production.run_controlled_production("expat-health-insurance", llm_provider=object(), deliver=True)
    finally:
        monkeypatch.undo()
    assert captured["wordpress"] is orchestration["production"]["boundary"]
    assert run["delivery"]["remote_status"] == "draft"
    assert run["publication"]["publish"] is False


def test_o7_g01_g02_controlled_delivery_resolves_to_human_review():
    orchestration, _ = _canonical_orchestration(live=True)
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(controlled_production, "run_production_orchestrator", lambda *a, **k: orchestration)
        run = controlled_production.run_controlled_production("expat-health-insurance", llm_provider=object(), deliver=True)
    finally:
        monkeypatch.undo()
    assert run["status"] == "human_review"
    assert run["human_review"] == {"required": True, "status": "pending"}


def test_o7_g01_g02_publication_intent_is_immutable():
    orchestration, _ = _canonical_orchestration(live=True)
    orchestration["production"]["wordpress"]["publish"] = True
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(controlled_production, "run_production_orchestrator", lambda *a, **k: orchestration)
        run = controlled_production.run_controlled_production("expat-health-insurance", llm_provider=object(), deliver=True)
    finally:
        monkeypatch.undo()
    assert run["status"] == "failed"
    assert run["publication"] == INTENT


def test_o7_g01_g02_lineage_conflict_fails_closed_deterministically():
    source = _artifacts(); source["optimization"]["lineage"]["report_id"] = "other_report"
    failures = []
    for _ in range(2):
        with pytest.raises(ProductionAssemblyEngineError) as exc:
            build_production_assembly(project_name="expat-health-insurance", artifacts=copy.deepcopy(source))
        failures.append((exc.value.code, exc.value.details))
    assert failures == [("LINEAGE_MISMATCH", ("report_id",)), ("LINEAGE_MISMATCH", ("report_id",))]


def test_o7_g01_g02_missing_checkpoint_fails_closed():
    run = controlled_production.create_controlled_production_run(project_name="expat-health-insurance", production_id="production_0123456789abcdef", orchestration_id="orchestration_0123456789abcdef")
    run = controlled_production.transition_controlled_production_run(run, status="running")
    with pytest.raises(ValueError, match="canonical production checkpoints"):
        controlled_production.transition_controlled_production_run(run, status="ready_for_delivery")


def test_o7_g01_g02_invalid_o7_transition_fails_closed():
    run = controlled_production.create_controlled_production_run(project_name="expat-health-insurance", production_id="production_0123456789abcdef", orchestration_id="orchestration_0123456789abcdef")
    with pytest.raises(ValueError, match="Invalid controlled production transition"):
        controlled_production.transition_controlled_production_run(run, status="human_review")


def test_o7_g01_g02_orchestration_failure_fails_closed():
    failed = _canonical_orchestration()[0]; failed["lifecycle_stage"] = "failed"; failed["error"] = {"type": "PackageError", "message": "package failed"}
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(controlled_production, "run_production_orchestrator", lambda *a, **k: failed)
        run = controlled_production.run_controlled_production("expat-health-insurance", llm_provider=object(), deliver=False)
    finally:
        monkeypatch.undo()
    assert run["status"] == "failed"
    assert run["publication"]["publish"] is False


def test_o7_g01_g02_wordpress_failure_fails_closed():
    failed = _canonical_orchestration(live=True)[0]
    failed["production"]["wordpress"]["delivery_status"] = "failed"
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(controlled_production, "run_production_orchestrator", lambda *a, **k: failed)
        run = controlled_production.run_controlled_production("expat-health-insurance", llm_provider=object(), deliver=True)
    finally:
        monkeypatch.undo()
    assert run["status"] == "failed"
    assert run["publication"]["publish"] is False


def test_o7_g01_g02_lineage_is_preserved_across_canonical_boundaries():
    _, captured = _canonical_orchestration()
    for artifact in (captured["assembly"], captured["package"]):
        assert {k: artifact["lineage"][k] for k in LINEAGE} == LINEAGE
        assert artifact["lineage"]["optimization_id"] == "optimization_123"
    assert captured["boundary"]["delivery_id"].startswith("delivery_")


def test_o7_g01_g02_end_to_end_traceability_without_o7_full_lineage_persistence():
    orchestration, _ = _canonical_orchestration()
    run = controlled_production.create_controlled_production_run(project_name="expat-health-insurance", production_id="production_0123456789abcdef", orchestration_id=orchestration["orchestration_id"])
    assert run["orchestration_id"] == orchestration["orchestration_id"]
    assert set(run) >= {"orchestration_id", "production_checkpoints"}
    assert not any(key in run for key in ("report_id", "decision_id", "strategy_id", "brief_id", "draft_id", "quality_id", "optimization_id"))
