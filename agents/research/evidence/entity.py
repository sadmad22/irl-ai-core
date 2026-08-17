from __future__ import annotations

from typing import Any

from .domain_common import build_observation


def build_entity_evidence(
    *,
    report_id: str,
    entity_id: str,
    entity_type: str,
    mentioned: bool,
    relevance: float | None = None,
    source: dict[str, Any],
    provenance: dict[str, Any],
    confidence: float,
    captured_at: str | None = None,
) -> list[dict[str, Any]]:
    """Build the minimum canonical Entity Evidence set.

    One observation records entity presence. An optional relevance score is a
    second independent observation; it is deliberately not derived here.
    """
    if not entity_id:
        raise ValueError("entity_id is required")
    if not entity_type:
        raise ValueError("entity_type is required")
    if relevance is not None and not 0 <= relevance <= 1:
        raise ValueError("relevance must be between 0 and 1")

    subject = {"type": "entity", "id": entity_id}
    evidence = [
        build_observation(
            report_id=report_id,
            domain="entity",
            subject=subject,
            claim={"type": "entity_presence", "attribute": "mentioned"},
            value={"type": "boolean", "data": mentioned},
            source=source,
            provenance=provenance,
            confidence=confidence,
            captured_at=captured_at,
        )
    ]
    if relevance is not None:
        evidence.append(
            build_observation(
                report_id=report_id,
                domain="entity",
                subject=subject,
                claim={"type": "entity_relevance", "attribute": "score"},
                value={"type": "numeric", "data": relevance},
                source=source,
                provenance=provenance,
                confidence=confidence,
                captured_at=captured_at,
            )
        )
    return evidence
