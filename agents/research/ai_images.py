from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_IMAGE_TYPES = {"hero", "section", "infographic", "comparison"}
_ASPECTS = {"16:9": (1600, 900), "4:3": (1200, 900), "1:1": (1200, 1200)}
_PLACEMENTS = {"hero", "section", "inline"}


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _require(document: dict[str, Any], field: str, label: str) -> Any:
    if field not in document:
        raise ValueError(f"{label}.{field} is required")
    return document[field]


def _require_ready(document: dict[str, Any], lifecycle: str, label: str) -> None:
    if document.get("lifecycle_stage") != lifecycle:
        raise ValueError(f"AI Images requires a {lifecycle} {label}")


def _lineage(*documents: dict[str, Any]) -> dict[str, str]:
    fields = ("brief_id", "report_id", "decision_id", "strategy_id")
    values: dict[str, str] = {}
    for field in fields:
        seen = {_clean(document.get(field)) for document in documents}
        if "" in seen:
            raise ValueError(f"AI Images requires {field} in all upstream artifacts")
        if len(seen) != 1:
            raise ValueError(f"AI Images lineage mismatch for {field}")
        values[field] = seen.pop()
    return values


def _section_index_map(strategy: dict[str, Any], draft: dict[str, Any]) -> list[tuple[int, str]]:
    sections = strategy.get("sections")
    draft_sections = draft.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("Content Strategy.sections must be a non-empty list")
    if not isinstance(draft_sections, list) or not draft_sections:
        raise ValueError("Article Draft.sections must be a non-empty list")

    headings = [_clean(section.get("heading")) if isinstance(section, dict) else "" for section in draft_sections]
    headings = [heading for heading in headings if heading]
    if not headings:
        raise ValueError("Article Draft.sections must contain headings")

    result: list[tuple[int, str]] = []
    for index, strategy_heading in enumerate(sections):
        heading = _clean(strategy_heading)
        if not heading:
            continue
        match = next((draft_heading for draft_heading in headings if draft_heading.casefold() == heading.casefold()), None)
        result.append((index, match or heading))
    return result


def _prompt(title: str, primary: str, heading: str, purpose: str) -> str:
    context = f"Article topic: {primary}."
    if title:
        context += f" Article title: {title}."
    return (
        "Create a professional editorial insurance illustration with no text, no logos, "
        "and no watermark. " + context + f" Section: {heading}. Purpose: {purpose}"
    )


def _image_id(spec_id_seed: dict[str, Any]) -> str:
    raw = json.dumps(spec_id_seed, sort_keys=True, separators=(",", ":"))
    return f"image_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _spec_id(lineage: dict[str, str], config_id: str, draft_id: str, images: list[dict[str, Any]]) -> str:
    raw = json.dumps({**lineage, "config_id": config_id, "draft_id": draft_id, "images": images}, sort_keys=True, separators=(",", ":"))
    return f"imgspec_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_ai_image_spec(
    *,
    content_strategy: dict[str, Any],
    article_config: dict[str, Any],
    article_draft: dict[str, Any],
) -> dict[str, Any]:
    """Build a deterministic, non-networked AI image specification from ready article artifacts."""
    _require_ready(content_strategy, "content_strategy_ready", "Content Strategy")
    _require_ready(article_config, "article_config_ready", "Article Configuration")
    _require_ready(article_draft, "draft_ready", "Article Draft")

    lineage = _lineage(content_strategy, article_draft)
    config_lineage = _lineage(article_config)
    if config_lineage != lineage:
        raise ValueError("AI Images lineage mismatch between Article Configuration and upstream artifacts")

    config_id = _clean(_require(article_config, "config_id", "Article Configuration"))
    draft_id = _clean(_require(article_draft, "draft_id", "Article Draft"))
    primary = _clean(_require(content_strategy, "primary_keyword", "Content Strategy"))
    title = _clean(article_draft.get("title"))

    if not config_id or not draft_id or not primary:
        raise ValueError("AI Images requires config_id, draft_id, and primary_keyword")

    section_map = _section_index_map(content_strategy, article_draft)
    images: list[dict[str, Any]] = []

    for position, (section_index, heading) in enumerate(section_map):
        if position == 0:
            image_type, aspect, placement, purpose = (
                "hero", "16:9", "hero", "Establish the article topic visually."
            )
        else:
            image_type, aspect, placement, purpose = (
                "section", "16:9", "section", f"Support the key concept covered in {heading}."
            )
        width, height = _ASPECTS[aspect]
        seed = {
            "draft_id": draft_id,
            "config_id": config_id,
            "section_index": section_index,
            "heading": heading,
            "image_type": image_type,
            "aspect_ratio": aspect,
        }
        images.append(
            {
                "image_id": _image_id(seed),
                "image_type": image_type,
                "section_index": section_index,
                "section_heading": heading,
                "purpose": purpose,
                "prompt": _prompt(title, primary, heading, purpose),
                "aspect_ratio": aspect,
                "width": width,
                "height": height,
                "placement": placement,
                "alt_text_status": "pending",
            }
        )

    if not images:
        raise ValueError("AI Images requires at least one image specification")

    image_spec_id = _spec_id(lineage, config_id, draft_id, images)
    return {
        "image_spec_id": image_spec_id,
        **lineage,
        "config_id": config_id,
        "draft_id": draft_id,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "ai_image_spec_ready",
        "images": copy.deepcopy(images),
        "constraints": {
            "network_access": False,
            "provider_call": False,
            "brand_style_included": False,
            "media_strategy_included": False,
        },
        "audit": {
            "method": "article_context_to_ai_image_specification",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
