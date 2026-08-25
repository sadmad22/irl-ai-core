from __future__ import annotations

from agents.research.article_draft_agent import run
from agents.research.editorial_readiness_gate import evaluate_editorial_readiness


def test_m7_real_article_reaches_wordpress_draft_ready_without_publish_permission():
    draft = run("m7-consultant-liability")
    result = evaluate_editorial_readiness(article_draft=draft)

    assert result["outcome"] == "passed", result
    assert result["target_lifecycle_stage"] == "wordpress_draft_ready"
    assert result["publish_allowed"] is False
    assert result["wordpress_write_allowed"] is False
    assert all(result["checks"].values()), result


def test_m7_real_article_readiness_is_non_mutating():
    draft = run("m7-consultant-liability")
    before = repr(draft)
    evaluate_editorial_readiness(article_draft=draft)
    assert repr(draft) == before
