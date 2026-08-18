from __future__ import annotations
import copy, pytest
from agents.research.publisher_agent import run_publisher_agent

def publication(): return {"publication_id":"p1","draft_id":"d1","brief_id":"b1","report_id":"r1","decision_id":"dec1","strategy_id":"s1","seo_strategy_id":"seo1","seo_validation_id":"sv1","review_id":"rev1","lifecycle_stage":"publication_ready","gate_status":"allowed","publication_status":"ready","evidence_refs":["e1"]}
def draft(): return {"draft_id":"d1","brief_id":"b1","report_id":"r1","decision_id":"dec1","strategy_id":"s1","lifecycle_stage":"draft_ready","title":"Accountant Insurance","primary_keyword":"accountant insurance","evidence_refs":["e1"],"sections":[{"heading":"Coverage","body":"content"}]}

def test_agent_prepares_allowed_publication_end_to_end():
 r=run_publisher_agent(publication=publication(),article_draft=draft()); assert r["lifecycle_stage"]=="publisher_ready"; assert r["execution_mode"]=="dry_run"; assert r["publish_status"]=="ready"
def test_agent_blocks_non_allowed_publication():
 p=publication(); p["gate_status"]="blocked"; p["publication_status"]="blocked"
 with pytest.raises(ValueError, match="allowed Publication Gate"):
  run_publisher_agent(publication=p,article_draft=draft())
def test_agent_is_deterministic_and_immutable():
 p,d=publication(),draft(); snap=copy.deepcopy((p,d)); a=run_publisher_agent(publication=p,article_draft=d); b=run_publisher_agent(publication=p,article_draft=d); assert a==b; assert (p,d)==snap
