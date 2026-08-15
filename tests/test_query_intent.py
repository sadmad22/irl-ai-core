from agents.research.analyzers.query_intent import classify_query_intent


def test_query_intent_is_independent_from_serp():
    result = classify_query_intent("best expat health insurance")

    assert result["keyword"] == "best expat health insurance"
    assert result["primary_intent"] == "Commercial"
    assert result["secondary_intent"] is None
    assert 0 <= result["confidence"] <= 1
    assert "best" in result["signals"]["Commercial"]


def test_query_without_explicit_signal_defaults_to_informational():
    result = classify_query_intent("expat health insurance")

    assert result["primary_intent"] == "Informational"
    assert result["secondary_intent"] is None
    assert result["confidence"] == 1.0
