from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

HOOK_TYPES = {
    "question",
    "benefit",
    "problem",
    "statistic",
    "scenario",
    "contrarian",
    "direct_answer",
}


def _contract_id(brief_id: str, payload: dict[str, Any]) -> str:
    raw = json.dumps({"brief_id": brief_id, "structure": payload}, sort_keys=True, ensure_ascii=False)
    return f"structure_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _range_block(value: Any, field: str) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    minimum = _positive_int(value.get("min", 0), f"{field}.min")
    maximum = _positive_int(value.get("max", minimum), f"{field}.max")
    if minimum > maximum:
        raise ValueError(f"{field}.min cannot exceed {field}.max")
    return {"min": minimum, "max": maximum}


def _hook(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("hook must be an object")
    required = value.get("required", True)
    if not isinstance(required, bool):
        raise ValueError("hook.required must be a boolean")
    hook_type = str(value.get("hook_type", "")).strip()
    if required and hook_type not in HOOK_TYPES:
        raise ValueError("hook.hook_type must be one of the supported hook types")
    if not required and hook_type and hook_type not in HOOK_TYPES:
        raise ValueError("hook.hook_type must be one of the supported hook types")
    return {"required": required, "hook_type": hook_type or None}


def _section_count(value: Any, field: str) -> dict[str, int]:
    return _range_block(value, field)


def _feature(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    enabled = value.get("enabled", True)
    required = value.get("required", False)
    if not isinstance(enabled, bool):
        raise ValueError(f"{field}.enabled must be a boolean")
    if not isinstance(required, bool):
        raise ValueError(f"{field}.required must be a boolean")
    if required and not enabled:
        raise ValueError(f"{field}.required cannot be true when {field}.enabled is false")
    counts = _range_block(value.get("count", {"min": 0, "max": 0}), f"{field}.count")
    if not enabled and (counts["min"] or counts["max"]):
        raise ValueError(f"{field}.count must be zero when {field}.enabled is false")
    if required and counts["min"] < 1:
        raise ValueError(f"{field}.count.min must be at least 1 when {field}.required is true")
    return {"enabled": enabled, "required": required, "count": counts}


def _faq(value: Any) -> dict[str, Any]:
    result = _feature(value, "faq")
    answer_required = value.get("answer_required", True) if isinstance(value, dict) else True
    if not isinstance(answer_required, bool):
        raise ValueError("faq.answer_required must be a boolean")
    result["answer_required"] = answer_required
    return result


def build_article_structure_contract(*, content_brief: dict[str, Any], structure: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize the Article Configuration & Structure contract.

    This contract defines structural requirements only. It does not write prose,
    choose SEO targets, evaluate evidence, or make an operational decision.
    """
    brief_id = str(content_brief.get("brief_id", "")).strip()
    report_id = str(content_brief.get("report_id", "")).strip()
    decision_id = str(content_brief.get("decision_id", "")).strip()
    strategy_id = str(content_brief.get("strategy_id", "")).strip()
    if not all((brief_id, report_id, decision_id, strategy_id)):
        raise ValueError("Content Brief lineage identifiers are required")
    if content_brief.get("lifecycle_stage") != "content_brief_ready":
        raise ValueError("Article Structure requires a content_brief_ready Content Brief")
    if not isinstance(structure, dict):
        raise ValueError("structure must be an object")

    hook = _hook(structure.get("hook", {}))
    conclusion_required = structure.get("conclusion", {}).get("required", True) if isinstance(structure.get("conclusion", {}), dict) else None
    if not isinstance(conclusion_required, bool):
        raise ValueError("conclusion.required must be a boolean")

    h3 = _section_count(structure.get("h3", {"min": 0, "max": 0}), "h3")
    tables = _feature(structure.get("tables", {}), "tables")
    lists = _feature(structure.get("lists", {}), "lists")
    faq = _faq(structure.get("faq", {}))

    payload = {
        "hook": hook,
        "conclusion": {"required": conclusion_required},
        "h3": h3,
        "tables": tables,
        "lists": lists,
        "faq": faq,
    }
    return {
        "structure_id": _contract_id(brief_id, payload),
        "brief_id": brief_id,
        "report_id": report_id,
        "decision_id": decision_id,
        "strategy_id": strategy_id,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "article_structure_ready",
        **payload,
        "audit": {
            "method": "content_brief_to_article_structure_contract",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
