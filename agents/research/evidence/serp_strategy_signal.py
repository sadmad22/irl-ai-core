from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

SCHEMA_VERSION = "1.0"
ANALYZER = "serp_strategy_signal"
ANALYZER_VERSION = "1.0"
METHOD = "rule_based"

STRATEGY_SIGNALS = {
    "informational",
    "commercial",
    "transactional",
    "navigational",
    "mixed",
    "indeterminate",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_id(prefix: str, value: str) -> str:
    digest = sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def build_serp_strategy_signal_evidence(
    analysis: dict,
    *,
    report_id: str,
    intent_alignment_evidence_id: str,
    captured_at: str | None = None,
) -> dict:
    """Convert SERP Strategy Signal analysis into one derived Evidence item."""
    if not isinstance(analysis, dict):
        raise TypeError("analysis must be a dictionary")
    if not report_id:
        raise ValueError("report_id is required")
    if not intent_alignment_evidence_id:
        raise ValueError("intent_alignment_evidence_id is required")

    keyword = str(analysis.get("keyword", "")).strip()
    strategy_signal = analysis.get("strategy_signal")
    confidence = analysis.get("confidence")

    if not keyword:
        raise ValueError("analysis.keyword is required")
    if strategy_signal not in STRATEGY_SIGNALS:
        raise ValueError("analysis.strategy_signal is invalid")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ValueError("analysis.confidence must be numeric")
    if not 0 <= confidence <= 1:
        raise ValueError("analysis.confidence must be between 0 and 1")

    captured = captured_at or _now_iso()

    return {
        "evidence_id": _stable_id(
            "ev_serp_strategy",
            f"{report_id}|{keyword}|{intent_alignment_evidence_id}|{strategy_signal}",
        ),
        "report_id": report_id,
        "schema_version": SCHEMA_VERSION,
        "type": "derived",
        "domain": "serp",
        "subject": {"type": "keyword", "id": keyword},
        "claim": {
            "type": "serp_strategy_signal",
            "attribute": "strategy_signal",
        },
        "value": {"type": "categorical", "data": strategy_signal},
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
        "derived_from": [intent_alignment_evidence_id],
        "captured_at": captured,
        "status": "active",
    }
