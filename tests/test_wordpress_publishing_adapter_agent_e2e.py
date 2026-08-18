from __future__ import annotations
import copy
import pytest
from agents.research.wordpress_publishing_adapter_agent import run_wordpress_publishing_adapter_agent

def publisher():
    return {"publisher_id":"pub1","publication_id":"p1","draft_id":"d1","brief_id":"b1","report_id":"r1","decision_id":"dec1","strategy_id":"s1","seo_strategy_id":"seo1","seo_validation_id":"sv1","review_id":"rev1","lifecycle_stage":"publisher_ready","publish_status":"ready","execution_mode":"dry_run","evidence_refs":["e1"]}

def draft():
    return {"draft_id":"d1","brief_id":"b1","report_id":"r1","decision_id":"dec1","strategy_id":"s1","lifecycle_stage":"draft_ready","title":"Accountant Insurance Guide","primary_keyword":"accountant insurance","content":"Article body","evidence_refs":["e1"]}

def test_agent_prepares_wordpress_request_end_to_end():
    result=run_wordpress_publishing_adapter_agent(publisher=publisher(),article_draft=draft())
    assert result["lifecycle_stage"]=="wordpress_publish_ready"
    assert result["platform"]=="wordpress"
    assert result["execution_mode"]=="dry_run"
    assert result["publish_status"]=="ready"

def test_agent_supports_live_request_preparation_without_network_io():
    result=run_wordpress_publishing_adapter_agent(publisher=publisher(),article_draft=draft(),execution_mode="live")
    assert result["execution_mode"]=="live"
    assert result["request_payload"]["status"]=="publish"

def test_agent_is_deterministic_and_immutable():
    p,d=publisher(),draft(); snapshot=copy.deepcopy((p,d))
    first=run_wordpress_publishing_adapter_agent(publisher=p,article_draft=d)
    second=run_wordpress_publishing_adapter_agent(publisher=p,article_draft=d)
    assert first==second
    assert (p,d)==snapshot

def test_agent_rejects_non_ready_publisher():
    p=publisher(); p["lifecycle_stage"]="pending"
    with pytest.raises(ValueError):
        run_wordpress_publishing_adapter_agent(publisher=p,article_draft=draft())
