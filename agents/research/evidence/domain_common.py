from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any


def deterministic_evidence_id(
    *, report_id: str, domain: str, subject: dict[str, Any], claim: dict[str, Any], value: dict[str, Any]
) -> str:
    payload = {
        "report_id": report_id,
        "domain": domain,
        "subject": subject,
        "claim": claim,
        "value": value,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return f"ev_{digest}"


def build_observation(
    *,
    report_id: str,
    domain: str,
    subject: dict[str, Any],
    claim: dict[str, Any],
    value: dict[str, Any],
    source: dict[str, Any],
    provenance: dict[str, Any],
    confidence: float,
    captured_at: str | None = None,
    evidence_id: str | None = None,
) -> dict[str, Any]:
    if not report_id:
        raise ValueError("report_id is required")
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")

    return {
        "evidence_id": evidence_id or deterministic_evidence_id(
            report_id=report_id,
            domain=domain,
            subject=subject,
            claim=claim,
            value=value,
        ),
        "report_id": report_id,
        "schema_version": "1.0",
        "type": "observation",
        "domain": domain,
        "subject": subject,
        "claim": claim,
        "value": value,
        "source": source,
        "provenance": provenance,
        "confidence": confidence,
        "relation": "supports",
        "derived_from": [],
        "captured_at": captured_at or datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
