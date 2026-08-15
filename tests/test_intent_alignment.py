from agents.research.analyzers.intent_alignment import analyze_intent_alignment


def test_aligned_intent():
    result = analyze_intent_alignment(
        {"keyword": "insurance guide", "primary_intent": "Informational"},
        {"keyword": "insurance guide", "dominant_intent": "Informational", "mixed_intent": False, "dominant_confidence": 0.9},
    )
    assert result["alignment"] == "aligned"


def test_mixed_intent():
    result = analyze_intent_alignment(
        {"keyword": "expat health insurance", "primary_intent": "Informational"},
        {"keyword": "expat health insurance", "dominant_intent": "Informational", "mixed_intent": True, "dominant_confidence": 0.63},
    )
    assert result["alignment"] == "mixed"


def test_misaligned_intent():
    result = analyze_intent_alignment(
        {"keyword": "expat health insurance", "primary_intent": "Informational"},
        {"keyword": "expat health insurance", "dominant_intent": "Commercial", "mixed_intent": False, "dominant_confidence": 0.8},
    )
    assert result["alignment"] == "misaligned"
