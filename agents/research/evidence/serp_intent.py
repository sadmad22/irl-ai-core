from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

SCHEMA_VERSION = "1.0"
ANALYZER = "serp_intent"
ANALYZER_VERSION = "1.0"
METHOD = "rule_based"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_id(prefix: str, value: str) -> str:
    digest = sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def build_serp_intent_evidence(
    analysis: dict,
    *,
    report_id: str,
    captured_at: str | None = None,
) -> list[dict]:
    """Convert SERP Intent Analyzer output into canonical evidence items.

    The result-level observations are the roots of the evidence lineage. Aggregate
    distribution, dominant-intent, and mixed-intent evidence are derived from those
    observations through ``derived_from`` references.
    """
    if not isinstance(analysis, dict):
        raise TypeError("analysis must be a dictionary")
    if not report_id:
        raise ValueError("report_id is required")

    keyword = str(analysis.get("keyword", "")).strip()
    results = analysis.get("results")
    if not keyword:
        raise ValueError("analysis.keyword is required")
    if not isinstance(results, list):
        raise ValueError("analysis.results must be a list")

    captured = captured_at or _now_iso()
    evidence: list[dict] = []
    result_evidence_ids: list[str] = []
    dominant_result_ids: list[str] = []
    dominant_intent = analysis.get("dominant_intent")

    for index, result in enumerate(results):
        if not isinstance(result, dict):
            raise ValueError(f"analysis.results[{index}] must be a dictionary")

        position = result.get("position")
        domain = str(result.get("domain") or "").strip()
        url = str(result.get("url") or "").strip()
        intent = result.get("intent")
        confidence = result.get("confidence")

        if not isinstance(intent, str) or not intent:
            raise ValueError(f"analysis.results[{index}].intent is required")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise ValueError(f"analysis.results[{index}].confidence must be numeric")
        if not 0 <= confidence <= 1:
            raise ValueError(f"analysis.results[{index}].confidence must be between 0 and 1")

        source_id = url or f"{keyword}:{position if position is not None else index}"
        result_key = f"{report_id}|{keyword}|{position}|{domain}|{url}|{index}"
        evidence_id = _stable_id("ev_serp_result", result_key)
        result_evidence_ids.append(evidence_id)

        if dominant_intent and intent == dominant_intent:
            dominant_result_ids.append(evidence_id)

        evidence.append(
            {
                "evidence_id": evidence_id,
                "report_id": report_id,
                "schema_version": SCHEMA_VERSION,
                "type": "observation",
                "domain": "serp",
                "subject": {
                    "type": "serp_result",
                    "id": f"{keyword}:{position if position is not None else index}",
                },
                "claim": {
                    "type": "serp_intent",
                    "attribute": "result_intent",
                },
                "value": {
                    "type": "categorical",
                    "data": intent,
                },
                "source": {
                    "type": "serp",
                    "source_id": source_id,
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
        )

    intent_distribution = analysis.get("intent_distribution", {})
    if not isinstance(intent_distribution, dict):
        raise ValueError("analysis.intent_distribution must be a dictionary")

    distribution_confidence = analysis.get("dominant_confidence", 0.0)
    if not isinstance(distribution_confidence, (int, float)) or isinstance(distribution_confidence, bool):
        raise ValueError("analysis.dominant_confidence must be numeric")
    if not 0 <= distribution_confidence <= 1:
        raise ValueError("analysis.dominant_confidence must be between 0 and 1")

    aggregate_subject = {"type": "keyword", "id": keyword}

    evidence.append(
        {
            "evidence_id": _stable_id("ev_serp_distribution", f"{report_id}|{keyword}"),
            "report_id": report_id,
            "schema_version": SCHEMA_VERSION,
            "type": "derived",
            "domain": "serp",
            "subject": aggregate_subject,
            "claim": {
                "type": "serp_intent",
                "attribute": "intent_distribution",
            },
            "value": {
                "type": "object",
                "data": intent_distribution,
            },
            "source": {
                "type": "serp",
                "source_id": keyword,
                "provider": "local",
                "retrieved_at": captured,
            },
            "provenance": {
                "analyzer": ANALYZER,
                "analyzer_version": ANALYZER_VERSION,
                "method": METHOD,
            },
            "confidence": distribution_confidence,
            "relation": "supports",
            "derived_from": result_evidence_ids,
            "captured_at": captured,
            "status": "active",
        }
    )

    if dominant_intent:
        evidence.append(
            {
                "evidence_id": _stable_id("ev_serp_dominant", f"{report_id}|{keyword}"),
                "report_id": report_id,
                "schema_version": SCHEMA_VERSION,
                "type": "derived",
                "domain": "serp",
                "subject": aggregate_subject,
                "claim": {
                    "type": "serp_intent",
                    "attribute": "dominant_intent",
                },
                "value": {
                    "type": "categorical",
                    "data": dominant_intent,
                },
                "source": {
                    "type": "serp",
                    "source_id": keyword,
                    "provider": "local",
                    "retrieved_at": captured,
                },
                "provenance": {
                    "analyzer": ANALYZER,
                    "analyzer_version": ANALYZER_VERSION,
                    "method": METHOD,
                },
                "confidence": distribution_confidence,
                "relation": "supports",
                "derived_from": dominant_result_ids,
                "captured_at": captured,
                "status": "active",
            }
        )

    mixed_intent = analysis.get("mixed_intent")
    if not isinstance(mixed_intent, bool):
        raise ValueError("analysis.mixed_intent must be boolean")

    evidence.append(
        {
            "evidence_id": _stable_id("ev_serp_mixed", f"{report_id}|{keyword}"),
            "report_id": report_id,
            "schema_version": SCHEMA_VERSION,
            "type": "derived",
            "domain": "serp",
            "subject": aggregate_subject,
            "claim": {
                "type": "serp_intent",
                "attribute": "mixed_intent",
            },
            "value": {
                "type": "boolean",
                "data": mixed_intent,
            },
            "source": {
                "type": "serp",
                "source_id": keyword,
                "provider": "local",
                "retrieved_at": captured,
            },
            "provenance": {
                "analyzer": ANALYZER,
                "analyzer_version": ANALYZER_VERSION,
                "method": METHOD,
            },
            "confidence": distribution_confidence,
            "relation": "qualifies" if mixed_intent else "neutral",
            "derived_from": result_evidence_ids,
            "captured_at": captured,
            "status": "active",
        }
    )

    return evidence
