from __future__ import annotations

from typing import Any

from .domain_common import build_observation

_ALLOWED_CLAIMS = {"authority_score", "topic_fit"}


def build_authority_evidence(
    *,
    report_id: str,
    subject_type: str,
    subject_id: str,
    claim_type: str,
    score: float,
    source: dict[str, Any],
    provenance: dict[str, Any],
    confidence: float,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Build one minimum Authority Evidence observation."""
    if claim_type not in _ALLOWED_CLAIMS:
        raise ValueError(f"unsupported authority claim: {claim_type}")
    if not 0 <= score <= 1:
        raise ValueError("authority score must be between 0 and 1")
    return build_observation(
        report_id=report_id,
        domain="authority",
        subject={"type": subject_type, "id": subject_id},
        claim={"type": "authority", "attribute": claim_type},
        value={"type": "numeric", "data": score},
        source=source,
        provenance=provenance,
        confidence=confidence,
        captured_at=captured_at,
    )
