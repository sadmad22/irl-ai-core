from __future__ import annotations

from typing import Any

from .domain_common import build_observation

_ALLOWED_CLAIMS = {"affiliate_potential", "adsense_potential", "conversion_potential", "commercial_value"}


def build_business_evidence(
    *,
    report_id: str,
    subject_type: str,
    subject_id: str,
    claim_type: str,
    value: str | float | int,
    source: dict[str, Any],
    provenance: dict[str, Any],
    confidence: float,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Build one minimum Business Evidence observation."""
    if claim_type not in _ALLOWED_CLAIMS:
        raise ValueError(f"unsupported business claim: {claim_type}")
    return build_observation(
        report_id=report_id,
        domain="business",
        subject={"type": subject_type, "id": subject_id},
        claim={"type": "business_value", "attribute": claim_type},
        value={"type": "categorical" if isinstance(value, str) else "numeric", "data": value},
        source=source,
        provenance=provenance,
        confidence=confidence,
        captured_at=captured_at,
    )
