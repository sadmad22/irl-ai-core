from __future__ import annotations
import copy,pytest
from agents.research.publisher import build_publisher

def draft(): return {"draft_id":"d1","brief_id":"b1","report_id":"r1","decision_id":"dec1","strategy_id":"s1","lifecycle_stage":"draft_ready","evidence_refs":["e1"]}
def pub(): return {"publication_id":"p1","draft_id":"d1","brief_id":"b1","report_id":"r1","decision_id":"dec1","strategy_id":"s1","seo_strategy_id":"seo1","seo_validation_id":"sv1","review_id":"rev1","lifecycle_stage":"publication_ready","gate_status":"allowed","publication_status":"ready"}

def test_prepares_ready_dry_run():
 r=build_publisher(article_draft=draft(),publication=pub()); assert r["publish_status"]=="ready"; assert r["execution_mode"]=="dry_run"; assert r["lifecycle_stage"]=="publisher_ready"
def test_requires_draft_ready():
 d=draft();d["lifecycle_stage"]="draft_pending"
 with pytest.raises(ValueError):build_publisher(article_draft=d,publication=pub())
def test_requires_publication_ready():
 p=pub();p["lifecycle_stage"]="pending"
 with pytest.raises(ValueError):build_publisher(article_draft=draft(),publication=p)
def test_requires_allowed_gate():
 p=pub();p["gate_status"]="blocked"
 with pytest.raises(ValueError):build_publisher(article_draft=draft(),publication=p)
def test_preserves_lineage():
 r=build_publisher(article_draft=draft(),publication=pub());assert [r[k] for k in ("draft_id","brief_id","report_id","decision_id","strategy_id")] == ["d1","b1","r1","dec1","s1"]
def test_requires_evidence():
 d=draft();d["evidence_refs"]=[]
 with pytest.raises(ValueError):build_publisher(article_draft=d,publication=pub())
def test_deterministic():
 assert build_publisher(article_draft=draft(),publication=pub())==build_publisher(article_draft=draft(),publication=pub())
def test_does_not_mutate_inputs():
 d,p=draft(),pub();s=copy.deepcopy((d,p));build_publisher(article_draft=d,publication=p);assert (d,p)==s
