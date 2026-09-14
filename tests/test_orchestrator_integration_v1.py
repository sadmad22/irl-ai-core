from __future__ import annotations

import copy

import pytest

from agents.research import production_orchestrator as orchestrator
from agents.research.production_assembly_engine import ProductionAssemblyEngineError, build_production_assembly
from agents.research.production_orchestrator import STAGES, execute_stage_plan

CANONICAL_STAGES = (
    "research", "intelligence", "configuration", "structure", "draft",
    "editorial_cleanup", "media", "linking", "optimization", "qa",
    "production_assembly", "article_package", "production_delivery_boundary", "wordpress_delivery",
)

LINEAGE = {"report_id": "report_123", "decision_id": "decision_123", "strategy_id": "strategy_123", "brief_id": "brief_123", "draft_id": "draft_123", "quality_id": "quality_123"}
PRODUCTION_INTENT = {"target": "wordpress", "mode": "wordpress_draft", "publish": False, "human_approval_required": True}
FINAL_OPTIMIZATION = {"optimization_id": "optimization_123", "schema_version": "1.0", "method_version": "v1", "lifecycle_stage": "optimization_ready", "seo_title": "Consultant Liability Insurance", "meta_description": "Compare consultant liability insurance coverage and costs.", "primary_keyword": "consultant liability insurance", "slug": "consultant-liability-insurance", "lineage": {"report_id": "report_123", "decision_id": "decision_123", "strategy_id": "strategy_123", "brief_id": "brief_123"}}


def test_orchestrator_uses_canonical_fourteen_stage_order():
    assert STAGES == CANONICAL_STAGES


def test_stage_plan_returns_canonical_production_checkpoints():
    def runner(stage, context):
        return {stage: {"status": "done"}}

    result = execute_stage_plan(project_name="demo", stage_runner=runner)

    assert result["completed_stages"] == list(CANONICAL_STAGES)
    assert result["remaining_stages"] == []
    assert result["current_stage"] is None
    assert result["error"] is None
    assert set(result["production"]) == {"assembly", "package", "boundary", "wordpress"}


def test_controlled_wordpress_completion_resolves_to_human_review():
    def runner(stage, context):
        if stage == "wordpress_delivery":
            return {
                "wordpress_delivery": {
                    "execution_mode": "live",
                    "response": {"remote_status": "draft"},
                },
                "production": {
                    "wordpress": {
                        "execution_mode": "live",
                        "delivery_status": "delivered",
                        "remote_status": "draft",
                        "publish": False,
                        "human_approval_required": True,
                    }
                },
            }
        return {stage: {"status": "done"}}

    result = execute_stage_plan(project_name="demo", stage_runner=runner)

    assert result["lifecycle_stage"] == "human_review"
    assert result["remaining_stages"] == []
    assert result["current_stage"] is None
    assert result["production"]["wordpress"]["publish"] is False
    assert result["production"]["wordpress"]["human_approval_required"] is True


def test_fail_stop_keeps_first_failed_stage_and_does_not_continue():
    calls = []

    def runner(stage, context):
        calls.append(stage)
        if stage == "production_assembly":
            raise RuntimeError("assembly failed")
        return {stage: {"status": "done"}}

    result = execute_stage_plan(project_name="demo", stage_runner=runner)

    assert result["lifecycle_stage"] == "failed"
    assert result["current_stage"] == "production_assembly"
    assert result["completed_stages"] == list(CANONICAL_STAGES[:10])
    assert result["remaining_stages"][0] == "production_assembly"
    assert calls == list(CANONICAL_STAGES[:10]) + ["production_assembly"]


def test_resume_requires_all_prior_canonical_checkpoints():
    def runner(stage, context):
        return {stage: {"status": "done"}}

    try:
        execute_stage_plan(project_name="demo", stage_runner=runner, start_stage="article_package", initial_outputs={"completed_stages": list(CANONICAL_STAGES[:10])})
    except ValueError as exc:
        assert "earlier stage checkpoints" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def _early_result():
    early = {"research_report": {}, "content_brief": {}, "article_draft": {}, "article_draft_quality": {}, "editorial_review": {}, "media": {}, "linking": {}, "final_optimization": copy.deepcopy(FINAL_OPTIMIZATION), "seo_validation": {}, "claim_audit": {}, "publication": {"gate_status": "allowed"}}
    early["article_draft"].update(LINEAGE)
    early["article_draft"]["lifecycle_stage"] = "draft_ready"
    early["article_draft_quality"].update(LINEAGE)
    early["article_draft_quality"]["lifecycle_stage"] = "article_draft_quality_ready"
    early["article_draft_quality"]["outcome"] = "passed"
    early["article_draft_quality"]["audit"] = {"validation_status": "validated"}
    return early


def _production_artifacts():
    return {
        "article_draft": {
            "draft_id": "draft_123", "brief_id": "brief_123", "report_id": "report_123", "decision_id": "decision_123", "strategy_id": "strategy_123", "lifecycle_stage": "draft_ready",
            "content_type": "guide", "primary_keyword": "expat health insurance", "title": "Expat Health Insurance Guide", "slug": "expat-health-insurance-guide",
            "sections": [{"section_id": "section_0", "heading": "Overview", "body": "Evidence-backed article text.", "purpose": "Explain the topic", "evidence_refs": ["evidence_1"], "claims": [{"claim_id": "claim_1", "text": "Evidence-backed article text.", "evidence_refs": ["evidence_1"], "grounding_status": "grounded"}]}],
            "tables": [],
        },
        "quality": {"quality_id": "quality_123", "draft_id": "draft_123", "brief_id": "brief_123", "report_id": "report_123", "decision_id": "decision_123", "strategy_id": "strategy_123", "lifecycle_stage": "article_draft_quality_ready", "outcome": "passed", "audit": {"validation_status": "validated"}},
        "claim_audit": {"outcome": "passed", "audit": {"validation_status": "validated"}},
        "editorial_review": {"outcome": "approved", "audit": {"validation_status": "validated"}},
        "optimization": {"optimization_id": "optimization_123", "lineage": {"report_id": "report_123", "decision_id": "decision_123", "strategy_id": "strategy_123", "brief_id": "brief_123"}, "seo_title": "Expat Health Insurance Guide", "meta_description": "A practical guide to expat health insurance.", "canonical_url": "https://insurancereviewlab.com/expat-health-insurance/"},
        "media": {"images": [{"image_id": "image_1", "section_index": 0, "placement": "hero", "prompt": "Editorial insurance illustration", "alt_text": "Expat health insurance illustration", "materialization_status": "materialized", "asset_ref": "media_1"}]},
        "linking": {"internal": [{"link_id": "link_internal_1", "section_index": 0, "target_url": "https://insurancereviewlab.com/insurance/", "anchor_text": "insurance coverage", "placement": "body"}], "external": []},
        "taxonomy": {"categories": ["Expat Insurance"], "tags": ["health insurance"]},
        "production_intent": copy.deepcopy(PRODUCTION_INTENT),
        "lineage": copy.deepcopy(LINEAGE),
    }


def test_build_orchestration_uses_assembly_package_boundary_and_adapter(monkeypatch):
    calls = []
    captured_assembly = {}
    early = _early_result()

    canonical = {"production_intent": dict(PRODUCTION_INTENT), "lineage": dict(LINEAGE)}
    assembly = {"assembly_id": "assembly_0123456789abcdef", "lifecycle_stage": "production_assembly_ready", "artifacts": canonical}
    package = {"identity": {"package_id": "package_0123456789abcdef", "lifecycle_stage": "delivery_ready"}, "audit": {"validation_status": "validated"}}
    boundary = {"delivery_id": "delivery_0123456789abcdef", "lifecycle_stage": "delivery_ready", "delivery_status": "ready"}
    adapter = {"execution_mode": "live", "response": {"platform_post_id": 123, "remote_status": "draft", "edit_url": "https://insurancereviewlab.com/wp-admin/post.php?post=123&action=edit"}}

    def fake_assembly(**kwargs):
        captured_assembly.update(kwargs)
        calls.append("assembly")
        return assembly
    def fake_package(**kwargs): calls.append("package"); return package
    def fake_boundary(**kwargs): calls.append("boundary"); return boundary
    def fake_adapter(**kwargs): calls.append("wordpress"); return adapter

    monkeypatch.setattr(orchestrator, "build_production_assembly", fake_assembly)
    monkeypatch.setattr(orchestrator, "build_article_package", fake_package)
    monkeypatch.setattr(orchestrator, "build_production_delivery_boundary", fake_boundary)
    monkeypatch.setattr(orchestrator, "deliver_wordpress_delivery_boundary", fake_adapter)

    result = orchestrator.build_production_orchestration(project_name="demo", result=early, deliver=True)

    assert calls == ["assembly", "package", "boundary", "wordpress"]
    assert captured_assembly["artifacts"]["optimization"] == FINAL_OPTIMIZATION
    assert "seo_validation" not in captured_assembly["artifacts"]
    assert result["lifecycle_stage"] == "human_review"
    assert result["completed_stages"][-4:] == list(CANONICAL_STAGES[-4:])
    assert result["production"]["wordpress"]["publish"] is False
    assert result["production"]["wordpress"]["human_approval_required"] is True


def test_actual_orchestrator_assembly_package_chain_preserves_g02_lineage(monkeypatch):
    captured = {}
    real_assembly = orchestrator.build_production_assembly
    real_package = orchestrator.build_article_package

    def capture_assembly(**kwargs):
        value = real_assembly(**kwargs)
        captured["assembly"] = value
        return value

    def capture_package(**kwargs):
        value = real_package(**kwargs)
        captured["package"] = value
        return value

    monkeypatch.setattr(orchestrator, "build_production_assembly", capture_assembly)
    monkeypatch.setattr(orchestrator, "build_article_package", capture_package)
    monkeypatch.setattr(orchestrator, "build_production_delivery_boundary", lambda **kwargs: {"delivery_id": "delivery_0123456789abcdef", "lifecycle_stage": "delivery_ready", "delivery_status": "ready"})

    result = orchestrator.build_production_orchestration(project_name="expat-health-insurance", result=_early_result() | _production_artifacts(), deliver=True, delivery_mode="dry_run")

    assembly = captured["assembly"]
    package = captured["package"]
    assert result["lifecycle_stage"] == "completed"
    assert {key: assembly["lineage"][key] for key in LINEAGE} == LINEAGE
    assert assembly["lineage"]["optimization_id"] == "optimization_123"
    assert {key: package["lineage"][key] for key in LINEAGE} == LINEAGE
    assert package["lineage"]["optimization_id"] == assembly["lineage"]["optimization_id"]
    assert package["optimization"]["seo_title"] == assembly["artifacts"]["optimization"]["seo_title"]
    assert package["optimization"]["meta_description"] == assembly["artifacts"]["optimization"]["meta_description"]


def test_g02_lineage_fields_do_not_disappear_at_assembly_package_boundary():
    source = _production_artifacts()
    assembly = build_production_assembly(project_name="expat-health-insurance", artifacts=source)
    assert set(LINEAGE).issubset(assembly["lineage"])
    assert "optimization_id" in assembly["lineage"]


def test_g02_failure_classification_is_deterministic():
    source = _production_artifacts()
    source["optimization"]["lineage"]["report_id"] = "other_report"
    messages = []
    for _ in range(2):
        try:
            build_production_assembly(project_name="expat-health-insurance", artifacts=copy.deepcopy(source))
        except ProductionAssemblyEngineError as exc:
            messages.append((exc.code, exc.details))
    assert messages == [("LINEAGE_MISMATCH", ("report_id",)), ("LINEAGE_MISMATCH", ("report_id",))]


def test_wordpress_adapter_receives_the_exact_canonical_boundary(monkeypatch):
    captured = {}
    early = _early_result()
    assembly = {
        "assembly_id": "assembly_0123456789abcdef",
        "lifecycle_stage": "production_assembly_ready",
        "artifacts": {"production_intent": dict(PRODUCTION_INTENT), "lineage": dict(LINEAGE)},
    }
    package = {
        "identity": {"package_id": "package_0123456789abcdef", "lifecycle_stage": "delivery_ready"},
        "audit": {"validation_status": "validated"},
    }
    boundary = {
        "delivery_id": "delivery_0123456789abcdef",
        "lifecycle_stage": "delivery_ready",
        "delivery_status": "ready",
        "target": "wordpress",
        "execution_mode": "live",
        "publication": copy.deepcopy(PRODUCTION_INTENT),
    }

    monkeypatch.setattr(orchestrator, "build_production_assembly", lambda **kwargs: assembly)
    monkeypatch.setattr(orchestrator, "build_article_package", lambda **kwargs: package)
    monkeypatch.setattr(orchestrator, "build_production_delivery_boundary", lambda **kwargs: boundary)

    def fake_adapter(**kwargs):
        captured.update(kwargs)
        return {
            "execution_mode": "live",
            "response": {"platform_post_id": 4957, "remote_status": "draft"},
        }

    monkeypatch.setattr(orchestrator, "deliver_wordpress_delivery_boundary", fake_adapter)

    connection = object()
    transport = object()
    result = orchestrator.build_production_orchestration(
        project_name="demo",
        result=early,
        deliver=True,
        connection=connection,
        transport=transport,
    )

    assert captured["boundary"] is boundary
    assert captured["connection"] is connection
    assert captured["transport"] is transport
    assert result["production"]["wordpress"]["platform_post_id"] == 4957
    assert result["production"]["wordpress"]["remote_status"] == "draft"
    assert result["lifecycle_stage"] == "human_review"


def test_wordpress_adapter_failure_stops_at_wordpress_delivery(monkeypatch):
    early = _early_result()
    assembly = {"assembly_id": "assembly_0123456789abcdef", "lifecycle_stage": "production_assembly_ready", "artifacts": {"production_intent": dict(PRODUCTION_INTENT), "lineage": dict(LINEAGE)}}
    package = {"identity": {"package_id": "package_0123456789abcdef", "lifecycle_stage": "delivery_ready"}, "audit": {"validation_status": "validated"}}
    boundary = {"delivery_id": "delivery_0123456789abcdef", "lifecycle_stage": "delivery_ready", "delivery_status": "ready"}

    monkeypatch.setattr(orchestrator, "build_production_assembly", lambda **kwargs: assembly)
    monkeypatch.setattr(orchestrator, "build_article_package", lambda **kwargs: package)
    monkeypatch.setattr(orchestrator, "build_production_delivery_boundary", lambda **kwargs: boundary)

    def fail_adapter(**kwargs):
        raise RuntimeError("wordpress transport failed")

    monkeypatch.setattr(orchestrator, "deliver_wordpress_delivery_boundary", fail_adapter)

    result = orchestrator.build_production_orchestration(project_name="demo", result=early, deliver=True)

    assert result["lifecycle_stage"] == "failed"
    assert result["current_stage"] == "wordpress_delivery"
    assert result["completed_stages"][-3:] == ["production_assembly", "article_package", "production_delivery_boundary"]
    assert result["production"]["wordpress"] == {}
    assert result["error"]["stage"] == "wordpress_delivery"
