from agents.research.analyzers.serp_strategy_signal import (
    analyze_serp_strategy_signal,
)


def test_aligned_informational_signal():
    result = analyze_serp_strategy_signal(
        {
            "keyword": "insurance guide",
            "query_primary_intent": "Informational",
            "serp_dominant_intent": "Informational",
            "alignment": "aligned",
            "confidence": 0.9,
        }
    )

    assert result["strategy_signal"] == "informational"


def test_mixed_signal():
    result = analyze_serp_strategy_signal(
        {
            "keyword": "expat health insurance",
            "query_primary_intent": "Informational",
            "serp_dominant_intent": "Informational",
            "alignment": "mixed",
            "confidence": 0.6337,
        }
    )

    assert result["strategy_signal"] == "mixed"


def test_misaligned_signal_is_conservative():
    result = analyze_serp_strategy_signal(
        {
            "keyword": "insurance quote",
            "query_primary_intent": "Informational",
            "serp_dominant_intent": "Transactional",
            "alignment": "misaligned",
            "confidence": 0.8,
        }
    )

    assert result["strategy_signal"] == "mixed"


def test_indeterminate_signal():
    result = analyze_serp_strategy_signal(
        {
            "keyword": "unknown",
            "query_primary_intent": None,
            "serp_dominant_intent": "Informational",
            "alignment": "indeterminate",
            "confidence": 0.0,
        }
    )

    assert result["strategy_signal"] == "indeterminate"