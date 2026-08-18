from __future__ import annotations

import copy
import pytest
from agents.research.seo_validation import validate_seo


def strategy():
    return {"seo_strategy_id":"seo_1","brief_id":"brief_1","report_id":"report_1","decision_id":"decision_1","strategy_id":"strategy_1","lifecycle_stage":"seo_strategy_ready","primary_keyword":"accountant insurance","heading_requirements":["Coverage"],"evidence_refs":["e1","e2"]}

def draft():
    return {"draft_id":"draft_1","brief_id":"brief_1","report_id":"report_1","decision_id":"decision_1","strategy_id":"strategy_1","lifecycle_stage":"draft_ready","title":"A Practical Guide to Accountant Insurance","primary_keyword":"accountant insurance","evidence_refs":["e1","e2"],"sections":[{"heading":"Coverage","purpose":"coverage","body":"Draft body"}]}

def test_passes_valid_draft():
    result = validate_seo(article_draft=draft(), seo_strategy=strategy())
    assert result["outcome"] == "passed"
    assert result["lifecycle_stage"] == "seo_validation_ready"

def test_preserves_lineage():
    result = validate_seo(article_draft=draft(), seo_strategy=strategy())
    assert result["draft_id"] == "draft_1"
    assert result["seo_strategy_id"] == "seo_1"
    assert result["evidence_refs"] == ["e1","e2"]

def test_is_deterministic():
    a = validate_seo(article_draft=draft(), seo_strategy=strategy())
    b = validate_seo(article_draft=draft(), seo_strategy=strategy())
    assert a == b

def test_requires_draft_ready():
    d = draft(); d["lifecycle_stage"] = "draft_pending"
    with pytest.raises(ValueError): validate_seo(article_draft=d, seo_strategy=strategy())

def test_requires_strategy_ready():
    s = strategy(); s["lifecycle_stage"] = "seo_strategy_pending"
    with pytest.raises(ValueError): validate_seo(article_draft=draft(), seo_strategy=s)

def test_detects_keyword_failure():
    d = draft(); d["title"] = "A Practical Guide"
    result = validate_seo(article_draft=d, seo_strategy=strategy())
    assert result["outcome"] == "needs_revision"
    assert result["checks"]["title"] is False

def test_rejects_lineage_mismatch():
    s = strategy(); s["brief_id"] = "other"
    with pytest.raises(ValueError): validate_seo(article_draft=draft(), seo_strategy=s)

def test_does_not_mutate_inputs():
    d, s = draft(), strategy(); ds, ss = copy.deepcopy(d), copy.deepcopy(s)
    validate_seo(article_draft=d, seo_strategy=s)
    assert d == ds and s == ss
