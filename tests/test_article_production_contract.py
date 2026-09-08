from shared.utils.article_production_contract import build_article_production


def _article():
    return {
        "draft_id": "draft_123",
        "brief_id": "brief_123",
        "report_id": "report_123",
        "decision_id": "decision_123",
        "strategy_id": "strategy_123",
        "schema_version": "1.0",
        "lifecycle_stage": "draft_ready",
        "title": "Example Article",
        "content_type": "guide",
        "primary_keyword": "example insurance",
        "sections": [{"heading": "Overview", "purpose": "Explain", "body": "Evidence-backed text", "evidence_refs": ["e1"], "claims": [{"claim_id": "c1", "text": "Supported claim", "evidence_refs": ["e1"], "grounding_status": "grounded"}]}],
        "evidence_refs": ["e1"],
        "editorial_constraints": [],
        "audit": {"method": "test", "version": "1", "validation_status": "pending"},
    }


def _quality():
    return {
        "quality_id": "quality_123",
        "draft_id": "draft_123",
        "brief_id": "brief_123",
        "report_id": "report_123",
        "decision_id": "decision_123",
        "strategy_id": "strategy_123",
        "schema_version": "1.0",
        "lifecycle_stage": "article_draft_quality_ready",
        "outcome": "passed",
        "checks": {},
        "findings": [],
        "evidence_refs": ["e1"],
        "audit": {"method": "test", "version": "1", "validation_status": "validated"},
    }


def test_builds_deterministic_production_envelope():
    first = build_article_production(article=_article(), quality=_quality())
    second = build_article_production(article=_article(), quality=_quality())

    assert first == second
    assert first["production_id"].startswith("production_")
    assert first["schema_version"] == "1.0"
    assert first["lifecycle_stage"] == "production_ready"
    assert first["lineage"]["draft_id"] == first["article"]["draft_id"]
    assert first["lineage"]["quality_id"] == first["quality"]["quality_id"]
    assert first["publication"] == {
        "mode": "wordpress_draft",
        "publish": False,
        "human_approval_required": True,
    }


def test_rejects_quality_without_passed_outcome():
    quality = _quality()
    quality["outcome"] = "needs_revision"

    try:
        build_article_production(article=_article(), quality=quality)
    except ValueError as exc:
        assert "passed" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_rejects_mismatched_lineage():
    quality = _quality()
    quality["draft_id"] = "draft_other"

    try:
        build_article_production(article=_article(), quality=quality)
    except ValueError as exc:
        assert "draft_id" in str(exc)
    else:
        raise AssertionError("expected ValueError")
