from agents.research.text_readability import analyze_readability, build_text_readability


def _lineage():
    return {"brief_id": "brief_1", "report_id": "report_1", "decision_id": "decision_1", "strategy_id": "strategy_1"}


def _draft(**overrides):
    data = {
        "draft_id": "draft_1",
        **_lineage(),
        "lifecycle_stage": "draft_ready",
        "sections": [
            {"heading": "Intro", "body": "Insurance helps people manage financial risk. A clear policy explains what is covered and what is excluded."},
            {"heading": "Details", "body": "Readers should compare limits, deductibles, exclusions, and claims requirements before choosing coverage."},
        ],
    }
    data.update(overrides)
    return data


def test_local_analyzer_returns_expected_metrics():
    metrics = analyze_readability("The cat sat. The cat slept.")
    assert metrics["word_count"] == 6
    assert metrics["sentence_count"] == 2
    assert metrics["syllable_count"] >= 6
    assert metrics["flesch_reading_ease"] > 80


def test_engine_is_deterministic():
    assert build_text_readability(article_draft=_draft()) == build_text_readability(article_draft=_draft())


def test_output_lifecycle_and_lineage():
    result = build_text_readability(article_draft=_draft())
    assert result["lifecycle_stage"] == "text_readability_ready"
    for key, value in _lineage().items():
        assert result[key] == value
    assert result["draft_id"] == "draft_1"


def test_local_metrics_are_present():
    metrics = build_text_readability(article_draft=_draft())["local_metrics"]
    assert metrics["word_count"] > 0
    assert metrics["sentence_count"] > 0
    assert metrics["flesch_kincaid_grade"] >= 0


def test_default_llm_assessment_is_not_requested():
    result = build_text_readability(article_draft=_draft())
    assert result["llm_assessment"] == {"status": "not_requested", "summary": "No LLM readability assessment was requested."}
    assert result["constraints"]["provider_call"] is False


def test_injected_llm_provider_is_supported():
    class Provider:
        def assess(self, *, text, local_metrics):
            assert text
            assert local_metrics["word_count"] > 0
            return {"status": "provided", "summary": "Readable for the target audience."}

    result = build_text_readability(article_draft=_draft(), llm_provider=Provider())
    assert result["llm_assessment"]["status"] == "provided"
    assert result["constraints"]["provider_call"] is True


def test_provider_result_is_copied():
    payload = {"status": "provided", "summary": "Good", "issues": ["long sentence"]}

    class Provider:
        def assess(self, *, text, local_metrics):
            return payload

    result = build_text_readability(article_draft=_draft(), llm_provider=Provider())
    payload["issues"].append("mutated")
    assert result["llm_assessment"]["issues"] == ["long sentence"]


def test_provider_must_expose_assess():
    try:
        build_text_readability(article_draft=_draft(), llm_provider=object())
    except ValueError as exc:
        assert "assess" in str(exc)
    else:
        raise AssertionError("Expected provider validation error")


def test_provider_must_return_object():
    class BadProvider:
        def assess(self, *, text, local_metrics):
            return "bad"

    try:
        build_text_readability(article_draft=_draft(), llm_provider=BadProvider())
    except ValueError as exc:
        assert "object" in str(exc)
    else:
        raise AssertionError("Expected provider result validation error")


def test_provider_fields_are_strict():
    class BadProvider:
        def assess(self, *, text, local_metrics):
            return {"status": "provided", "unexpected": True}

    try:
        build_text_readability(article_draft=_draft(), llm_provider=BadProvider())
    except ValueError as exc:
        assert "fields" in str(exc)
    else:
        raise AssertionError("Expected field validation error")


def test_provider_status_is_validated():
    class BadProvider:
        def assess(self, *, text, local_metrics):
            return {"status": "failed"}

    try:
        build_text_readability(article_draft=_draft(), llm_provider=BadProvider())
    except ValueError as exc:
        assert "status" in str(exc)
    else:
        raise AssertionError("Expected status validation error")


def test_missing_lifecycle_is_rejected():
    try:
        build_text_readability(article_draft=_draft(lifecycle_stage="drafting"))
    except ValueError as exc:
        assert "draft_ready" in str(exc)
    else:
        raise AssertionError("Expected lifecycle error")


def test_missing_lineage_is_rejected():
    draft = _draft()
    del draft["strategy_id"]
    try:
        build_text_readability(article_draft=draft)
    except ValueError as exc:
        assert "strategy_id" in str(exc)
    else:
        raise AssertionError("Expected lineage error")


def test_sections_must_be_non_empty():
    try:
        build_text_readability(article_draft=_draft(sections=[]))
    except ValueError as exc:
        assert "sections" in str(exc)
    else:
        raise AssertionError("Expected sections error")


def test_section_bodies_must_contain_text():
    try:
        build_text_readability(article_draft=_draft(sections=[{"heading": "Intro", "body": ""}]))
    except ValueError as exc:
        assert "body" in str(exc)
    else:
        raise AssertionError("Expected body error")


def test_target_grade_must_be_positive():
    for value in (0, -1, True):
        try:
            build_text_readability(article_draft=_draft(), target_grade=value)
        except ValueError as exc:
            assert "target_grade" in str(exc)
        else:
            raise AssertionError("Expected target grade error")


def test_high_grade_can_need_revision():
    long_words = " ".join(["uncharacteristically"] * 80) + "."
    result = build_text_readability(article_draft=_draft(sections=[{"heading": "Text", "body": long_words}]))
    assert result["outcome"] == "needs_revision"


def test_target_grade_changes_outcome():
    draft = _draft(sections=[{"heading": "Text", "body": "Insurance coverage protects businesses from financial loss. Policies contain terms, exclusions, and conditions."}])
    easy = build_text_readability(article_draft=draft, target_grade=20)
    strict = build_text_readability(article_draft=draft, target_grade=1)
    assert easy["outcome"] == "passed"
    assert strict["outcome"] == "needs_revision"


def test_input_draft_is_not_mutated():
    draft = _draft()
    before = repr(draft)
    build_text_readability(article_draft=draft)
    assert repr(draft) == before


def test_network_access_is_always_false():
    assert build_text_readability(article_draft=_draft())["constraints"]["network_access"] is False


def test_source_and_draft_mutation_are_false():
    constraints = build_text_readability(article_draft=_draft())["constraints"]
    assert constraints["source_mutation"] is False
    assert constraints["draft_mutation"] is False


def test_id_changes_when_input_text_changes():
    first = build_text_readability(article_draft=_draft())
    second = build_text_readability(article_draft=_draft(sections=[{"heading": "Intro", "body": "Insurance protects against financial risk."}]))
    assert first["text_readability_id"] != second["text_readability_id"]


def test_id_changes_when_llm_assessment_changes():
    class ProviderA:
        def assess(self, *, text, local_metrics):
            return {"status": "provided", "summary": "A"}

    class ProviderB:
        def assess(self, *, text, local_metrics):
            return {"status": "provided", "summary": "B"}

    first = build_text_readability(article_draft=_draft(), llm_provider=ProviderA())
    second = build_text_readability(article_draft=_draft(), llm_provider=ProviderB())
    assert first["text_readability_id"] != second["text_readability_id"]


def test_audit_metadata():
    assert build_text_readability(article_draft=_draft())["audit"] == {
        "method": "local_readability_metrics_plus_injected_llm_assessment",
        "version": "v1",
        "validation_status": "validated",
    }
