from __future__ import annotations

import copy

import pytest

from agents.research.editorial_review import build_editorial_review


def draft():
    return {
        "draft_id":"draft_1","brief_id":"brief_1","report_id":"report_1","decision_id":"decision_1","strategy_id":"strategy_1",
        "schema_version":"1.0","lifecycle_stage":"draft_ready","title":"A Practical Guide to Accountant Insurance",
        "content_type":"guide","primary_keyword":"accountant insurance","evidence_refs":["e1","e2"],
        "sections":[{"heading":"Coverage","purpose":"explain coverage","body":"Use evidence and mark any claim that still requires editorial verification before publication."}],
        "editorial_constraints":[],
    }


def test_review_approves_valid_draft():
    result = build_editorial_review(article_draft=draft())
    assert result["outcome"] == "approved"
    assert result["lifecycle_stage"] == "editorial_review_ready"


def test_review_preserves_lineage():
    result = build_editorial_review(article_draft=draft())
    for key in ("draft_id","brief_id","report_id","decision_id","strategy_id"):
        assert result[key] == draft()[key]
    assert result["evidence_refs"] == ["e1","e2"]


def test_review_is_deterministic():
    first = build_editorial_review(article_draft=draft())
    second = build_editorial_review(article_draft=draft())
    assert first == second


def test_review_requires_draft_ready():
    bad = draft(); bad["lifecycle_stage"] = "draft_pending"
    with pytest.raises(ValueError):
        build_editorial_review(article_draft=bad)


def test_review_requires_evidence():
    bad = draft(); bad["evidence_refs"] = []
    result = build_editorial_review(article_draft=bad)
    assert result["outcome"] == "needs_revision"
    assert result["checks"]["evidence_coverage"] is False


def test_review_flags_unverified_claims():
    bad = draft(); bad["sections"] = [{"heading":"Coverage","purpose":"explain","body":"A factual claim."}]
    result = build_editorial_review(article_draft=bad)
    assert result["outcome"] == "needs_revision"
    assert any(f["category"] == "unsupported_claims" for f in result["findings"])


def test_review_does_not_mutate_draft():
    original = draft(); snapshot = copy.deepcopy(original)
    build_editorial_review(article_draft=original)
    assert original == snapshot
