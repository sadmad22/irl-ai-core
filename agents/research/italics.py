from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
LIFECYCLE_STAGE = "italics_ready"
POLICY = "editorial_emphasis_only"


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value


def _max_per_section(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("italics.max_per_section must be a non-negative integer")
    return value


def _normalize(italics: Any) -> dict[str, Any]:
    if italics is None:
        italics = {}
    if not isinstance(italics, dict):
        raise ValueError("italics must be an object")

    allowed = {"enabled", "required", "max_per_section", "policy"}
    unknown = set(italics) - allowed
    if unknown:
        raise ValueError(f"italics contains unsupported fields: {sorted(unknown)}")

    enabled = italics.get("enabled", False)
    required = italics.get("required", False)
    maximum = italics.get("max_per_section", 0)
    policy = italics.get("policy", POLICY)

    enabled = _bool(enabled, "italics.enabled")
    required = _bool(required, "italics.required")
    maximum = _max_per_section(maximum)

    if required and not enabled:
        raise ValueError("italics: required cannot be true when disabled")
    if not enabled and maximum != 0:
        raise ValueError("italics: disabled feature max_per_section must be zero")
    if enabled and maximum < 1:
        raise ValueError("italics.max_per_section must be at least 1 when enabled")
    if policy != POLICY:
        raise ValueError("italics.policy must be editorial_emphasis_only")

    return {
        "enabled": enabled,
        "required": required,
        "max_per_section": maximum,
        "policy": POLICY,
    }


def _italics_id(lineage: dict[str, str], settings: dict[str, Any]) -> str:
    payload = {
        **lineage,
        "italics": settings,
        "schema_version": SCHEMA_VERSION,
        "method_version": METHOD_VERSION,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"italics_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _validate_outline_editor(outline_editor: dict[str, Any]) -> None:
    if not isinstance(outline_editor, dict):
        raise ValueError("Outline Editor must be an object")
    if outline_editor.get("lifecycle_stage") != "outline_editor_ready":
        raise ValueError("Italics requires an outline_editor_ready Outline Editor")
    for field in (
        "outline_editor_id",
        "brief_id",
        "report_id",
        "decision_id",
        "strategy_id",
        "config_id",
        "structure_id",
        "details_to_include_id",
    ):
        _text(outline_editor.get(field), f"Outline Editor.{field}")
    sections = outline_editor.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("Outline Editor.sections must contain at least one section")


def build_italics_contract(
    *,
    outline_editor: dict[str, Any],
    italics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic Italics editorial-formatting contract.

    The contract configures optional editorial emphasis only. It does not modify
    prose, insert markup, generate text, perform SEO work, or call an LLM/provider.
    Actual application of italics belongs to a downstream editorial formatter.
    """
    _validate_outline_editor(outline_editor)
    settings = _normalize(italics)

    lineage = {
        "brief_id": outline_editor["brief_id"],
        "report_id": outline_editor["report_id"],
        "decision_id": outline_editor["decision_id"],
        "strategy_id": outline_editor["strategy_id"],
        "config_id": outline_editor["config_id"],
        "outline_editor_id": outline_editor["outline_editor_id"],
        "details_to_include_id": outline_editor["details_to_include_id"],
    }

    return {
        "italics_id": _italics_id(lineage, settings),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": LIFECYCLE_STAGE,
        "italics": settings,
        "audit": {
            "method": "deterministic-italics-editorial-contract",
            "method_version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
