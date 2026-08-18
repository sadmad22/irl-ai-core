from __future__ import annotations
import copy
import pytest
from agents.research.wordpress_publishing_adapter import build_wordpress_publish_request

def publisher(): return {"publisher_id":"pub1","publication_id":"p1","draft_id":"d1","lifecycle_stage":"publisher_ready","publish_status":"ready"}
def draft(): return {"draft_id":"d1","lifecycle_stage":"draft_ready","title":"Accountant Insurance","slug":"accountant-insurance","excerpt":"Guide","evidence_refs":["e1"],"sections":[{"heading":"Coverage","body":"Coverage details."},{"heading":"Cost","body":"Cost details."}]}

def test_builds_wordpress_dry_run_request():
 r=build_wordpress_publish_request(publisher=publisher(),article_draft=draft()); assert r["platform"]=="wordpress"; assert r["endpoint"]=="/wp-json/wp/v2/posts"; assert r["method"]=="POST"; assert r["execution_mode"]=="dry_run"; assert r["request_payload"]["status"]=="draft"
def test_live_mode_prepares_publish_status_without_network_io():
 r=build_wordpress_publish_request(publisher=publisher(),article_draft=draft(),execution_mode="live"); assert r["execution_mode"]=="live"; assert r["request_payload"]["status"]=="publish"
def test_requires_publisher_ready():
 p=publisher(); p["lifecycle_stage"]="pending"
 with pytest.raises(ValueError): build_wordpress_publish_request(publisher=p,article_draft=draft())
def test_requires_publisher_ready_status():
 p=publisher(); p["publish_status"]="blocked"
 with pytest.raises(ValueError): build_wordpress_publish_request(publisher=p,article_draft=draft())
def test_requires_draft_ready():
 d=draft(); d["lifecycle_stage"]="draft_pending"
 with pytest.raises(ValueError): build_wordpress_publish_request(publisher=publisher(),article_draft=d)
def test_rejects_lineage_mismatch():
 p=publisher(); p["draft_id"]="other"
 with pytest.raises(ValueError): build_wordpress_publish_request(publisher=p,article_draft=draft())
def test_requires_evidence_refs():
 d=draft(); d["evidence_refs"]=[]
 with pytest.raises(ValueError): build_wordpress_publish_request(publisher=publisher(),article_draft=d)
def test_requires_content():
 d=draft(); d["sections"]=[]
 with pytest.raises(ValueError): build_wordpress_publish_request(publisher=publisher(),article_draft=d)
def test_is_deterministic_and_immutable():
 p,d=publisher(),draft(); snap=copy.deepcopy((p,d)); a=build_wordpress_publish_request(publisher=p,article_draft=d); b=build_wordpress_publish_request(publisher=p,article_draft=d); assert a==b; assert (p,d)==snap
