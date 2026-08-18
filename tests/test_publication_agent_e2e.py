from __future__ import annotations
import copy, pytest
from agents.research.publication_agent import run_publication_agent

def draft(): return {"draft_id":"d1","brief_id":"b1","report_id":"r1","decision_id":"dec1","strategy_id":"s1","lifecycle_stage":"draft_ready","evidence_refs":["e1"]}
def seo(): return {"seo_strategy_id":"seo1","seo_validation_id":"sv1","draft_id":"d1","brief_id":"b1","report_id":"r1","decision_id":"dec1","strategy_id":"s1","lifecycle_stage":"seo_validation_ready","outcome":"passed"}
def review(): return {"review_id":"rev1","draft_id":"d1","brief_id":"b1","report_id":"r1","decision_id":"dec1","strategy_id":"s1","lifecycle_stage":"editorial_review_ready","outcome":"approved"}

def test_agent_allows_publication_end_to_end():
 r=run_publication_agent(article_draft=draft(),seo_validation=seo(),editorial_review=review()); assert r["gate_status"]=="allowed"; assert r["publication_status"]=="ready"; assert r["lifecycle_stage"]=="publication_ready"
def test_agent_blocks_when_any_gate_fails():
 s=seo(); s["outcome"]="needs_revision"; r=run_publication_agent(article_draft=draft(),seo_validation=s,editorial_review=review()); assert r["gate_status"]=="blocked"; assert r["publication_status"]=="blocked"
def test_agent_is_deterministic_and_does_not_mutate_inputs():
 d,s,e=draft(),seo(),review(); snap=copy.deepcopy((d,s,e)); a=run_publication_agent(article_draft=d,seo_validation=s,editorial_review=e); b=run_publication_agent(article_draft=d,seo_validation=s,editorial_review=e); assert a==b; assert (d,s,e)==snap
