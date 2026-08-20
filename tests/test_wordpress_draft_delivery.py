from __future__ import annotations
import copy
import pytest
import agents.research.wordpress_draft_delivery as draft_delivery
from agents.research.wordpress_draft_delivery import build_wordpress_draft_delivery

def publisher(): return {"publisher_id":"pub1","publication_id":"p1","draft_id":"d1","lifecycle_stage":"publisher_ready","publish_status":"ready","evidence_refs":["e1"]}
def draft(): return {"draft_id":"d1","lifecycle_stage":"draft_ready","title":"Accountant Insurance Guide","sections":[{"heading":"Coverage","body":"Article body"}],"evidence_refs":["e1"]}

def test_builds_draft_delivery():
 r=build_wordpress_draft_delivery(publisher=publisher(),article_draft=draft()); assert r["lifecycle_stage"]=="wordpress_draft_ready"; assert r["delivery_status"]=="ready"; assert r["request_payload"]["status"]=="draft"
def test_live_mode_still_forces_draft():
 r=build_wordpress_draft_delivery(publisher=publisher(),article_draft=draft(),execution_mode="live"); assert r["execution_mode"]=="live"; assert r["request_payload"]["status"]=="draft"
def test_status_cannot_be_overridden_by_input():
 d=draft(); d["status"]="publish"; r=build_wordpress_draft_delivery(publisher=publisher(),article_draft=d); assert r["request_payload"]["status"]=="draft"
def test_invalid_execution_mode_rejected():
 with pytest.raises(ValueError): build_wordpress_draft_delivery(publisher=publisher(),article_draft=draft(),execution_mode="publish")
def test_requires_ready_publisher():
 p=publisher(); p["lifecycle_stage"]="pending"
 with pytest.raises(ValueError): build_wordpress_draft_delivery(publisher=p,article_draft=draft())
def test_requires_ready_draft():
 d=draft(); d["lifecycle_stage"]="pending"
 with pytest.raises(ValueError): build_wordpress_draft_delivery(publisher=publisher(),article_draft=d)
def test_preserves_lineage_and_evidence():
 r=build_wordpress_draft_delivery(publisher=publisher(),article_draft=draft()); assert r["publisher_id"]=="pub1"; assert r["publication_id"]=="p1"; assert r["draft_id"]=="d1"; assert r["evidence_refs"]==["e1"]
def test_deterministic_and_immutable():
 p,d=publisher(),draft(); snap=copy.deepcopy((p,d)); a=build_wordpress_draft_delivery(publisher=p,article_draft=d); b=build_wordpress_draft_delivery(publisher=p,article_draft=d); assert a==b; assert (p,d)==snap

def test_security_invariant_live_mode_can_never_emit_publish(monkeypatch):
    def malicious_adapter(**kwargs):
        return {
            "adapter_id":"adapter1",
            "publisher_id":"pub1",
            "publication_id":"p1",
            "draft_id":"d1",
            "request_payload":{"title":"Injected","content":"Injected","status":"publish"},
            "evidence_refs":["e1"],
        }

    monkeypatch.setattr(draft_delivery, "build_wordpress_publishing_request", malicious_adapter)
    result = draft_delivery.build_wordpress_draft_delivery(
        publisher=publisher(),
        article_draft=draft(),
        execution_mode="live",
    )

    assert result["execution_mode"] == "live"
    assert result["request_payload"]["status"] == "draft"
    assert result["lifecycle_stage"] == "wordpress_draft_ready"
    assert result["delivery_status"] == "ready"
