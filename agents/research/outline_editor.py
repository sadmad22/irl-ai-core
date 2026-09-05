from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
LIFECYCLE_STAGE = "outline_editor_ready"

CONTENT_TYPES = {"guide", "comparison", "buyer_guide", "article"}
ALLOWED_LEVELS = {"H2", "H3"}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value


def _positive(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _outline_id(lineage: dict[str, str], sections: list[dict[str, Any]]) -> str:
    raw = json.dumps({"lineage": lineage, "sections": sections}, sort_keys=True, ensure_ascii=False)
    return f"outline_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _validate_lineage(strategy: dict[str, Any], config: dict[str, Any], structure: dict[str, Any], details: dict[str, Any]) -> None:
    if strategy.get("lifecycle_stage") != "content_strategy_ready":
        raise ValueError("Outline Editor requires a content_strategy_ready Content Strategy")
    if config.get("lifecycle_stage") != "article_config_ready":
        raise ValueError("Outline Editor requires an article_config_ready Article Configuration")
    if structure.get("lifecycle_stage") != "article_structure_ready":
        raise ValueError("Outline Editor requires an article_structure_ready Article Structure")
    if details.get("lifecycle_stage") != "details_to_include_ready":
        raise ValueError("Outline Editor requires a details_to_include_ready Details to Include contract")

    for left, right, name in (
        (config, strategy, "report_id"),
        (config, strategy, "decision_id"),
        (config, strategy, "strategy_id"),
        (structure, config, "report_id"),
        (structure, config, "decision_id"),
        (structure, config, "strategy_id"),
        (details, config, "report_id"),
        (details, config, "decision_id"),
        (details, config, "strategy_id"),
        (details, config, "config_id"),
    ):
        if left.get(name) != right.get(name):
            raise ValueError(f"Lineage mismatch for {name}")

    if structure.get("brief_id") != config.get("brief_id"):
        raise ValueError("Article Structure.brief_id must match Article Configuration.brief_id")
    if details.get("brief_id") != config.get("brief_id"):
        raise ValueError("Details to Include.brief_id must match Article Configuration.brief_id")
    if config.get("article_type") != strategy.get("content_type"):
        raise ValueError("Article Configuration.article_type must match Content Strategy.content_type")


def _default_sections(strategy: dict[str, Any]) -> list[dict[str, Any]]:
    source = strategy.get("sections")
    if not isinstance(source, list) or not source:
        raise ValueError("Content Strategy.sections must contain at least one section")
    result: list[dict[str, Any]] = []
    for index, heading in enumerate(source, 1):
        result.append({
            "order": index,
            "heading": _text(heading, f"sections[{index}].heading"),
            "level": "H2",
            "required": True,
        })
    return result


def _normalize_sections(strategy: dict[str, Any], outline: Any) -> list[dict[str, Any]]:
    if outline is None:
        return _default_sections(strategy)
    if not isinstance(outline, list) or not outline:
        raise ValueError("outline.sections must be a non-empty list")
    result: list[dict[str, Any]] = []
    seen_orders: set[int] = set()
    for index, item in enumerate(outline, 1):
        if not isinstance(item, dict):
            raise ValueError(f"outline.sections[{index}] must be an object")
        order = _positive(item.get("order", index), f"outline.sections[{index}].order")
        if order in seen_orders:
            raise ValueError("outline section order values must be unique")
        seen_orders.add(order)
        heading = _text(item.get("heading"), f"outline.sections[{index}].heading")
        level = item.get("level", "H2")
        if level not in ALLOWED_LEVELS:
            raise ValueError(f"outline.sections[{index}].level must be H2 or H3")
        required = _bool(item.get("required", True), f"outline.sections[{index}].required")
        purpose = item.get("purpose")
        if purpose is not None:
            purpose = _text(purpose, f"outline.sections[{index}].purpose")
        notes = item.get("notes")
        if notes is not None:
            notes = _text(notes, f"outline.sections[{index}].notes")
        result.append({"order": order, "heading": heading, "level": level, "required": required, **({"purpose": purpose} if purpose is not None else {}), **({"notes": notes} if notes is not None else {})})
    result.sort(key=lambda item: item["order"])
    if [item["order"] for item in result] != list(range(1, len(result) + 1)):
        raise ValueError("outline section order must be contiguous starting at 1")
    return result


def build_outline_editor_contract(*, content_strategy: dict[str, Any], article_configuration: dict[str, Any], article_structure: dict[str, Any], details_to_include: dict[str, Any], outline: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build a deterministic, editable article outline from the IRL Content Strategy.

    The editor preserves upstream structure and configuration constraints. It does
    not write prose, generate headings with an LLM, perform SEO analysis, or alter
    the upstream contracts.
    """
    _validate_lineage(content_strategy, article_configuration, article_structure, details_to_include)
    content_type = _text(content_strategy.get("content_type"), "content_strategy.content_type")
    if content_type not in CONTENT_TYPES:
        raise ValueError("Unsupported Content Strategy content_type")

    sections = _normalize_sections(content_strategy, outline)
    structure_h3 = article_structure.get("h3") or {"min": 0, "max": 0}
    h3_count = sum(item["level"] == "H3" for item in sections)
    if h3_count < structure_h3.get("min", 0) or h3_count > structure_h3.get("max", h3_count):
        raise ValueError("Outline H3 count violates Article Structure bounds")

    for feature_name in ("tables", "lists", "faq"):
        feature = article_structure.get(feature_name) or {}
        if feature.get("required") and not feature.get("enabled"):
            raise ValueError(f"Article Structure requires disabled feature: {feature_name}")

    lineage = {
        "brief_id": article_configuration["brief_id"],
        "report_id": article_configuration["report_id"],
        "decision_id": article_configuration["decision_id"],
        "strategy_id": article_configuration["strategy_id"],
        "config_id": article_configuration["config_id"],
        "structure_id": article_structure["structure_id"],
        "details_to_include_id": details_to_include["details_to_include_id"],
    }
    return {
        "outline_editor_id": _outline_id(lineage, sections),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": LIFECYCLE_STAGE,
        "article_type": article_configuration["article_type"],
        "primary_keyword": _text(content_strategy.get("primary_keyword"), "content_strategy.primary_keyword"),
        "sections": sections,
        "constraints": {
            "h3": {"min": structure_h3.get("min", 0), "max": structure_h3.get("max", 0)},
            "tables": article_structure["tables"],
            "lists": article_structure["lists"],
            "faq": article_structure["faq"],
            "details_to_include": details_to_include["details_to_include"],
        },
        "audit": {"method": "content_strategy_to_outline_editor", "method_version": METHOD_VERSION, "validation_status": "validated"},
    }
