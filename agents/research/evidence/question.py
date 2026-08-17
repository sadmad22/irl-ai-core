from __future__ import annotations

from typing import Any

from .domain_common import build_observation


def build_question_evidence(
    *,
    report_id: str,
    subject_type: str,
    subject_id: str,
    question_count: int,
    source: dict[str, Any],
    provenance: dict[str, Any],
    confidence: float,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Build the minimum Question Evidence: observed question frequency."""
    if question_count < 0:
        raise ValueError("question_count must be non-negative")
    return build_observation(
        report_id=report_id,
        domain="question",
        subject={"type": subject_type, "id": subject_id},
        claim={"type": "question_frequency", "attribute": "count"},
        value={"type": "numeric", "data": question_count},
        source=source,
        provenance=provenance,
        confidence=confidence,
        captured_at=captured_at,
    )
