from __future__ import annotations
import copy, pytest
from agents.research.publication import build_publication_gate

def draft(): return {"draft_id":"d1","brief_id":"b1","report_id":"r1","decision_id":"dec1","strategy_id":"s1","lifecycle_stage":"draft_ready","evidence_refs":["e1"]}
def seo(): return {"seo_strategy_id":"seo1","seo_validation_id":"sv1","draft_id":"d1","brief_id":"b1","report_id":"r1","decision_id":"dec1","strategy_id":"s1","lifecycle_stage":"seo_validation_ready","outcome":"passed"}
def review(): return {"review_id":"rev1","draft_id":"d1","brief_id":"b1","report_id":"r1","decision_id":"dec1","strategy_id":"s1","lifecycle_stage":"editorial_review_ready","outcome":"approved"}

def test_allows_publication_when_both_gates_pass():
 r=build_publication_gate(article_draft=draft(),seo_validation=seo(),editorial_review=review()); assert r["gate_status"]=="allowed"; assert r["publication_status"]=="ready"
def test_blocks_failed_seo():
 s=seo(); s["outcome"]="needs_revision"; assert build_publication_gate(article_draft=draft(),seo_validation=s,editorial_review=review())["gate_status"]=="blocked"
def test_blocks_unapproved_editorial():
 e=review(); e["outcome"]="needs_revision"; assert build_publication_gate(article_draft=draft(),seo_validation=seo(),editorial_review=e)["gate_status"]=="blocked"
def test_requires_draft_ready():
 d=draft(); d["lifecycle_stage"]="draft_pending"
 with pytest.raises(ValueError): build_publication_gate(article_draft=d,seo_validation=seo(),editorial_review=review())
def test_requires_seo_validation_ready():
 s=seo(); s["lifecycle_stage"]="pending"
 with pytest.raises(ValueError): build_publication_gate(article_draft=draft(),seo_validation=s,editorial_review=review())
def test_requires_editorial_review_ready():
 e=review(); e["lifecycle_stage"]="pending"
 with pytest.raises(ValueError): build_publication_gate(article_draft=draft(),seo_validation=seo(),editorial_review=e)
def test_preserves_lineage():
 r=build_publication_gate(article_draft=draft(),seo_validation=seo(),editorial_review=review())
 assert [r[k] for k in ("draft_id","brief_id","report_id","decision_id","strategy_id")]==["d1","b1","r1","dec1","s1"]
def test_deterministic_and_immutable():
 d,s,e=draft(),seo(),review(); snap=copy.deepcopy((d,s,e)); a=build_publication_gate(article_draft=d,seo_validation=s,editorial_review=e); b=build_publication_gate(article_draft=d,seo_validation=s,editorial_review=e); assert a==b; assert (d,s,e)==snap
