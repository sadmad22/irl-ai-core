from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

QUALITY_WEIGHT = 0.65
SEO_WEIGHT = 0.35
SEO_SCORED_CHECKS = ("primary_keyword", "title", "headings")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _require_lifecycle(source: dict[str, Any], expected: str) -> None:
    if source.get("lifecycle_stage") != expected:
        raise ValueError(f"Content Score requires lifecycle_stage={expected}")


def _lineage(integration: dict[str, Any]) -> dict[str, str]:
    return {
        key: _text(integration.get(key), f"integration.{key}")
        for key in ("brief_id", "report_id", "decision_id", "strategy_id")
    }


def _score_checks(checks: Any, field: str, selected: tuple[str, ...] | None = None) -> tuple[float, dict[str, bool]]:
    if not isinstance(checks, dict):
        raise ValueError(f"{field} checks must be an object")
    keys = selected if selected is not None else tuple(checks.keys())
    if not keys:
        raise ValueError(f"{field} requires at least one check")
    selected_checks: dict[str, bool] = {}
    for key in keys:
        value = checks.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"{field}.{key} must be boolean")
        selected_checks[key] = value
    passed = sum(value is True for value in selected_checks.values())
    return round((passed / len(selected_checks)) * 100, 2), selected_checks


def _score_id(lineage: dict[str, str], payload: dict[str, Any]) -> str:
    raw = json.dumps({"lineage": lineage, "payload": payload}, sort_keys=True, ensure_ascii=False)
    return f"content_score_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _context_signal(integration: dict[str, Any], name: str) -> dict[str, Any]:
    signal = integration.get("signals", {}).get(name)
    if not isinstance(signal, dict) or signal.get("available") is not True:
        raise ValueError(f"P0 Integration signal {name} must be available")
    return {
        "available": True,
        "scored": False,
        "reason": "No normalized scoring metric is defined for this signal in v1.",
        "source": dict(signal.get("source", {})),
    }


def build_content_score(*, p0_integration: dict[str, Any]) -> dict[str, Any]:
    """Calculate a deterministic Content Score from the P0 Integration contract.

    v1 scores only non-overlapping, boolean quality and SEO checks. Semantic SEO,
    SERP/competitive analysis, and Article Configuration remain explicit context
    until normalized metrics and targets are defined for them.
    """
    _require_lifecycle(p0_integration, "p0_integration_ready")

    signals = p0_integration.get("signals")
    if not isinstance(signals, dict):
        raise ValueError("P0 Integration signals must be an object")

    lineage = _lineage(p0_integration)
    quality = signals.get("quality")
    seo = signals.get("seo")
    if not isinstance(quality, dict) or not isinstance(seo, dict):
        raise ValueError("P0 Integration requires quality and seo signals")
    if quality.get("available") is not True or seo.get("available") is not True:
        raise ValueError("P0 Integration quality and seo signals must be available")

    quality_score, quality_checks = _score_checks(quality.get("checks"), "quality")
    seo_score, seo_checks = _score_checks(seo.get("checks"), "seo", SEO_SCORED_CHECKS)
    score = round((quality_score * QUALITY_WEIGHT) + (seo_score * SEO_WEIGHT), 2)

    components = {
        "quality": {
            "score": quality_score,
            "weight": QUALITY_WEIGHT,
            "checks": quality_checks,
            "source": dict(quality.get("source", {})),
        },
        "seo": {
            "score": seo_score,
            "weight": SEO_WEIGHT,
            "checks": seo_checks,
            "source": dict(seo.get("source", {})),
        },
    }

    payload = {
        "score": score,
        "components": components,
        "context": {
            "semantic": _context_signal(p0_integration, "semantic"),
            "competitive": _context_signal(p0_integration, "competitive"),
            "configuration": _context_signal(p0_integration, "configuration"),
        },
        "scoring_policy": {
            "quality_weight": QUALITY_WEIGHT,
            "seo_weight": SEO_WEIGHT,
            "seo_scored_checks": list(SEO_SCORED_CHECKS),
            "version": METHOD_VERSION,
        },
    }

    return {
        "content_score_id": _score_id(lineage, payload),
        **lineage,
        "integration_id": _text(p0_integration.get("integration_id"), "integration.integration_id"),
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "content_score_ready",
        **payload,
        "audit": {
            "method": "p0_quality_and_seo_weighted_score",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
