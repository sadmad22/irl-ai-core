from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

SCHEMA_VERSION = "1.0"
ANALYZER = "intent_alignment"
ANALYZER_VERSION = "1.0"
METHOD = "rule_based"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_id(prefix: str, value: str) -> str:
    digest = sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def build_intent_alignment_evidence(
    analysis: dict,
    *,
    report_id: str,
    query_intent_evidence_id: str,
    serp_intent_evidence_ids: list[str],
    captured_at: str | None = None,
) -> dict:
    """Convert Intent Alignment Analyzer output into one derived Evidence item.

    Alignment is derived from evidence produced by two upstream domains: the
    query-intent observation and one or more SERP-intent observations.
    """
    if not isinstance(analysis, dict):
        raise TypeError("analysis must be a dictionary")
    if not report_id:
        raise ValueError("report_id is required")
    if not query_intent_evidence_id:
        raise ValueError("query_intent_evidence_id is required")
    if not isinstance(serp_intent_evidence_ids, list) or not serp_intent_evidence_ids:
        raise ValueError("serp_intent_evidence_ids must be a non-empty list")
    if any(not isinstance(item, str) or not item for item in serp_intent_evidence_ids):
        raise ValueError("serp_intent_evidence_ids must contain non-empty strings")

    keyword = str(analysis.get("keyword", "")).strip()
    alignment = analysis.get("alignment")
    confidence = analysis.get("confidence")

    if not keyword:
        raise ValueError("analysis.keyword is required")
    if not isinstance(alignment, str) or not alignment:
        raise ValueError("analysis.alignment is required")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ValueError("analysis.confidence must be numeric")
    if not 0 <= confidence <= 1:
        raise ValueError("analysis.confidence must be between 0 and 1")

    captured = captured_at or _now_iso()
    lineage = list(dict.fromkeys([query_intent_evidence_id, *serp_intent_evidence_ids]))

    return {
        "evidence_id": _stable_id(
            "ev_intent_alignment",
            f"{report_id}|{keyword}|{query_intent_evidence_id}|{','.join(lineage[1:])}",
        ),
        "report_id": report_id,
        "schema_version": SCHEMA_VERSION,
        "type": "derived",
        "domain": "intent",
        "subject": {"type": "keyword", "id": keyword},
        "claim": {"type": "intent_alignment", "attribute": "alignment"},
        "value": {"type": "categorical", "data": alignment},
        "source": {
            "type": "derived",
            "source_id": None,
            "provider": None,
            "retrieved_at": None,
        },
        "provenance": {
            "analyzer": ANALYZER,
            "analyzer_version": ANALYZER_VERSION,
            "method": METHOD,
        },
        "confidence": confidence,
        "relation": "supports",
        "derived_from": lineage,
        "captured_at": captured,
        "status": "active",
    }
