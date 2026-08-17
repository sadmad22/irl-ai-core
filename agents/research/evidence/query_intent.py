from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

SCHEMA_VERSION = "1.0"
ANALYZER = "query_intent"
ANALYZER_VERSION = "1.0"
METHOD = "rule_based"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_query_intent_evidence(
    analysis: dict,
    *,
    report_id: str,
    evidence_id: str | None = None,
    captured_at: str | None = None,
) -> dict:
    """Convert Query Intent Analyzer output into one canonical Evidence item."""
    if not isinstance(analysis, dict):
        raise TypeError("analysis must be a dictionary")
    if not report_id:
        raise ValueError("report_id is required")

    keyword = str(analysis.get("keyword", "")).strip()
    primary_intent = analysis.get("primary_intent")
    confidence = analysis.get("confidence")

    if not keyword:
        raise ValueError("analysis.keyword is required")
    if not isinstance(primary_intent, str) or not primary_intent:
        raise ValueError("analysis.primary_intent is required")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ValueError("analysis.confidence must be numeric")
    if not 0 <= confidence <= 1:
        raise ValueError("analysis.confidence must be between 0 and 1")

    captured = captured_at or _now_iso()

    return {
        "evidence_id": evidence_id or f"ev_{uuid4().hex}",
        "report_id": report_id,
        "schema_version": SCHEMA_VERSION,
        "type": "observation",
        "domain": "intent",
        "subject": {"type": "keyword", "id": keyword},
        "claim": {"type": "query_intent", "attribute": "primary_intent"},
        "value": {"type": "categorical", "data": primary_intent},
        "source": {
            "type": "query",
            "source_id": keyword,
            "provider": "local",
            "retrieved_at": captured,
        },
        "provenance": {
            "analyzer": ANALYZER,
            "analyzer_version": ANALYZER_VERSION,
            "method": METHOD,
        },
        "confidence": confidence,
        "relation": "supports",
        "derived_from": [],
        "captured_at": captured,
        "status": "active",
    }
