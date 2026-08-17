from __future__ import annotations

import re
from typing import Any

METHOD_VERSION = "question-v1"

_QUESTION_START = re.compile(r"\b(?:what|which|how|why|when|where|who|can|does|do|is|are|should|does)\b", re.I)


def analyze_questions(serp_analysis: dict[str, Any]) -> dict[str, Any]:
    """Count question-shaped SERP demand deterministically."""
    results = serp_analysis.get("results", []) or []
    questions: list[dict[str, Any]] = []
    for result in results:
        title = str(result.get("title", ""))
        snippet = str(result.get("snippet", ""))
        text = f"{title} {snippet}".strip()
        explicit = text.count("?")
        interrogative = 1 if _QUESTION_START.search(text) else 0
        count = explicit + interrogative
        if count:
            questions.append({
                "text": title or snippet[:160],
                "source_position": result.get("position"),
                "count": count,
            })
    total = sum(item["count"] for item in questions)
    return {
        "questions": questions,
        "question_count": total,
        "result_question_count": len(questions),
        "method": METHOD_VERSION,
    }
