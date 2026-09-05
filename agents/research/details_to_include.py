from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_CONTENT_TYPES = {"guide", "comparison", "buyer_guide", "article"}

_DEFAULT_DETAILS: dict[str, Any] = {
    "key_takeaways": {
        "enabled": True,
        "required": True,
        "count": {"min": 3, "target": 4, "max": 5},
    },
    "quotes": {
        "enabled": True,
        "required": False,
        "count": {"min": 0, "target": 1, "max": 2},
        "source_requirement": "verified_source_evidence",
        "attribution_required": True,
        "evidence_gate": "verified_evidence_required",
    },
    "bold": {
        "enabled": True,
        "required": False,
        "max_per_section": 3,
        "policy": "editorial_emphasis_only",
    },
}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _ready(document: dict[str, Any], lifecycle: str, label: str) -> None:
    if not isinstance(document, dict):
        raise ValueError(f"{label} must be an object")
    if document.get("lifecycle_stage") != lifecycle:
        raise ValueError(f"{label} requires {lifecycle}")


def _lineage(strategy: dict[str, Any], config: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for field in ("report_id", "decision_id", "strategy_id"):
        strategy_value = _text(strategy.get(field), f"Content Strategy.{field}")
        config_value = _text(config.get(field), f"Article Configuration.{field}")
        if strategy_value != config_value:
            raise ValueError(f"Lineage mismatch for {field}")
        result[field] = strategy_value
    result["brief_id"] = _text(config.get("brief_id"), "Article Configuration.brief_id")
    result["config_id"] = _text(config.get("config_id"), "Article Configuration.config_id")
    return result


def _count(value: Any, field: str) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    values: dict[str, int] = {}
    for name in ("min", "target", "max"):
        number = value.get(name)
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise ValueError(f"{field}.{name} must be a non-negative integer")
        values[name] = number
    if not values["min"] <= values["target"] <= values["max"]:
        raise ValueError(f"{field} must satisfy min <= target <= max")
    return values


def _feature(value: Any, field: str, *, kind: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    enabled = value.get("enabled")
    required = value.get("required")
    if not isinstance(enabled, bool) or not isinstance(required, bool):
        raise ValueError(f"{field}.enabled and {field}.required must be booleans")
    if required and not enabled:
        raise ValueError(f"{field}: required cannot be true when disabled")

    count = _count(value.get("count"), f"{field}.count")
    if not enabled and count != {"min": 0, "target": 0, "max": 0}:
        raise ValueError(f"{field}: disabled feature count must be zero")
    if required and count["min"] < 1:
        raise ValueError(f"{field}.count.min must be at least 1 when required")

    result = {"enabled": enabled, "required": required, "count": count}
    if kind == "quotes":
        source_requirement = value.get("source_requirement", "verified_source_evidence")
        attribution_required = value.get("attribution_required", True)
        evidence_gate = value.get("evidence_gate", "verified_evidence_required")
        if source_requirement != "verified_source_evidence":
            raise ValueError("quotes.source_requirement must be verified_source_evidence")
        if attribution_required is not True:
            raise ValueError("quotes.attribution_required must be true")
        if evidence_gate != "verified_evidence_required":
            raise ValueError("quotes.evidence_gate must be verified_evidence_required")
        result.update(
            {
                "source_requirement": source_requirement,
                "attribution_required": attribution_required,
                "evidence_gate": evidence_gate,
            }
        )
    return result


def _bold(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("bold must be an object")
    enabled = value.get("enabled")
    required = value.get("required")
    if not isinstance(enabled, bool) or not isinstance(required, bool):
        raise ValueError("bold.enabled and bold.required must be booleans")
    if required and not enabled:
        raise ValueError("bold: required cannot be true when disabled")
    maximum = value.get("max_per_section")
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 0:
        raise ValueError("bold.max_per_section must be a non-negative integer")
    if not enabled and maximum != 0:
        raise ValueError("bold: disabled feature max_per_section must be zero")
    if enabled and maximum < 1:
        raise ValueError("bold.max_per_section must be at least 1 when enabled")
    if value.get("policy", "editorial_emphasis_only") != "editorial_emphasis_only":
        raise ValueError("bold.policy must be editorial_emphasis_only")
    return {
        "enabled": enabled,
        "required": required,
        "max_per_section": maximum,
        "policy": "editorial_emphasis_only",
    }


def _validate_details(details: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(details, dict):
        raise ValueError("details must be an object")
    allowed = {"key_takeaways", "quotes", "bold"}
    unknown = set(details) - allowed
    if unknown:
        raise ValueError(f"details contains unsupported fields: {sorted(unknown)}")
    merged = copy.deepcopy(_DEFAULT_DETAILS)
    for name, value in details.items():
        if name == "bold":
            merged[name] = _bold(value)
        elif name == "key_takeaways":
            merged[name] = _feature(value, "key_takeaways", kind="takeaways")
        else:
            merged[name] = _feature(value, "quotes", kind="quotes")
    return merged


def _details_id(lineage: dict[str, str], article_type: str, details: dict[str, Any]) -> str:
    payload = {
        **lineage,
        "article_type": article_type,
        "details_to_include": details,
        "schema_version": SCHEMA_VERSION,
        "method_version": METHOD_VERSION,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"details_to_include_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_details_to_include(
    *,
    content_strategy: dict[str, Any],
    article_config: dict[str, Any],
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic Details to Include contract for downstream editorial stages.

    This engine configures editorial requirements only. It does not generate
    takeaways, quotes, prose, formatting, or LLM/provider calls. Quotes remain
    gated by verified source evidence and require attribution downstream.
    """
    _ready(content_strategy, "content_strategy_ready", "Content Strategy")
    _ready(article_config, "article_config_ready", "Article Configuration")
    lineage = _lineage(content_strategy, article_config)

    strategy_type = _text(content_strategy.get("content_type"), "Content Strategy.content_type")
    article_type = _text(article_config.get("article_type"), "Article Configuration.article_type")
    if strategy_type not in _CONTENT_TYPES:
        raise ValueError(f"Unsupported content strategy content_type: {strategy_type}")
    if article_type not in _CONTENT_TYPES:
        raise ValueError(f"Unsupported article type: {article_type}")
    if strategy_type != article_type:
        raise ValueError("Content type and article type must match")

    normalized = _validate_details(details or {})
    return {
        "details_to_include_id": _details_id(lineage, article_type, normalized),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "details_to_include_ready",
        "details_to_include": normalized,
        "audit": {
            "method": "deterministic-details-to-include",
            "method_version": METHOD_VERSION,
        },
    }
