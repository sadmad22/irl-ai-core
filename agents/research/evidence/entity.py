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

    The builder records presence and entity classification as independent
    observations. Relevance is optional and remains an independent observation.
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
        ),
        build_observation(
            report_id=report_id,
            domain="entity",
            subject=subject,
            claim={"type": "entity_classification", "attribute": "type"},
            value={"type": "categorical", "data": entity_type},
            source=source,
            provenance=provenance,
            confidence=confidence,
            captured_at=captured_at,
        ),
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
