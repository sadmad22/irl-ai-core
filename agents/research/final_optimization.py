from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlparse

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
LIFECYCLE_STAGE = "optimization_ready"

_REQUIRED_LINEAGE = ("report_id", "decision_id", "strategy_id", "brief_id")
_REQUIRED_FINAL_VALUES = ("seo_title", "meta_description", "primary_keyword", "slug")
_ALLOWED_FINAL_VALUE_FIELDS = set(_REQUIRED_FINAL_VALUES) | {"canonical_url", "source_refs", "audit"}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _canonical_url(value: Any) -> str:
    url = _text(value, "final_values.canonical_url")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("final_values.canonical_url must be a valid HTTP(S) URL")
    return url


def _lineage(
    *,
    report: dict[str, Any],
    decision: dict[str, Any],
    strategy: dict[str, Any],
    brief: dict[str, Any],
    supplied: dict[str, Any] | None,
) -> dict[str, str]:
    sources = {
        "report_id": _text(report.get("report_id"), "report.report_id"),
        "decision_id": _text(decision.get("decision_id"), "decision.decision_id"),
        "strategy_id": _text(strategy.get("strategy_id"), "strategy.strategy_id"),
        "brief_id": _text(brief.get("brief_id"), "brief.brief_id"),
    }

    if supplied is None:
        return sources
    if not isinstance(supplied, dict):
        raise ValueError("lineage must be an object")

    for key, value in supplied.items():
        if key not in _REQUIRED_LINEAGE:
            raise ValueError(f"Unsupported lineage field: {key}")
        supplied_value = _text(value, f"lineage.{key}")
        if supplied_value != sources[key]:
            raise ValueError(f"Conflicting lineage for {key}")

    return sources


def _final_values(final_values: Any) -> dict[str, Any]:
    if final_values is None:
        raise ValueError("final_values is required")
    if not isinstance(final_values, dict):
        raise ValueError("final_values must be an object")

    unsupported = set(final_values) - _ALLOWED_FINAL_VALUE_FIELDS
    if unsupported:
        raise ValueError(f"Unsupported final_values fields: {sorted(unsupported)}")

    result: dict[str, Any] = {}
    for field in _REQUIRED_FINAL_VALUES:
        result[field] = _text(final_values.get(field), f"final_values.{field}")

    if "canonical_url" in final_values:
        result["canonical_url"] = _canonical_url(final_values["canonical_url"])

    if "source_refs" in final_values:
        refs = final_values["source_refs"]
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise ValueError("final_values.source_refs must be a list of non-empty strings")
        result["source_refs"] = [ref.strip() for ref in refs]

    if "audit" in final_values:
        audit = final_values["audit"]
        if not isinstance(audit, dict) or audit:
            raise ValueError("final_values.audit must be an empty object in v1")
        result["audit"] = {}

    return result


def _optimization_id(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"optimization_{digest}"


def build_final_optimization(
    *,
    report: dict[str, Any],
    decision: dict[str, Any],
    strategy: dict[str, Any],
    brief: dict[str, Any],
    final_values: dict[str, Any] | None = None,
    method_version: str = METHOD_VERSION,
    lineage: dict[str, Any] | None = None,
    **unsupported: Any,
) -> dict[str, Any]:
    """Build the canonical Final Optimization Artifact v1.

    The builder accepts only explicit upstream identities and explicit final SEO
    values. It performs deterministic validation/binding and never discovers,
    infers, rewrites, publishes, or calls external services.
    """
    if unsupported:
        raise ValueError(f"Unsupported build inputs: {sorted(unsupported)}")
    if method_version != METHOD_VERSION:
        raise ValueError(f"method_version must be {METHOD_VERSION}")

    bound_lineage = _lineage(
        report=report,
        decision=decision,
        strategy=strategy,
        brief=brief,
        supplied=lineage,
    )
    values = _final_values(final_values)

    canonical = {
        "schema_version": SCHEMA_VERSION,
        "method_version": method_version,
        "lifecycle_stage": LIFECYCLE_STAGE,
        **values,
        "lineage": bound_lineage,
    }
    optimization_id = _optimization_id(canonical)
    return {"optimization_id": optimization_id, **canonical}
