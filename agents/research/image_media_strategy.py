from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_PLACEMENTS = {"hero", "section", "inline"}
_ROLES = {"hero", "explain", "illustrate", "compare", "break", "support"}
_DENSITIES = {"low", "moderate", "high"}
_IMAGE_TYPES = {"hero", "section", "infographic", "comparison"}


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _ready(document: dict[str, Any], lifecycle: str, label: str) -> None:
    if document.get("lifecycle_stage") != lifecycle:
        raise ValueError(f"Image Media Strategy requires a {lifecycle} {label}")


def _lineage(image_style: dict[str, Any]) -> dict[str, str]:
    fields = (
        "brief_id", "report_id", "decision_id", "strategy_id",
        "config_id", "draft_id", "image_spec_id", "image_style_id",
    )
    result: dict[str, str] = {}
    for field in fields:
        value = _clean(image_style.get(field))
        if not value:
            raise ValueError(f"Image Media Strategy requires {field} in Image Style")
        result[field] = value
    return result


def _strategy(images: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(images)
    density = "low" if count <= 2 else "moderate" if count <= 6 else "high"
    if density not in _DENSITIES:
        raise ValueError(f"Unsupported media density: {density}")
    return {
        "density": density,
        "max_images": max(1, min(50, count)),
        "hero_required": any(image["image_type"] == "hero" for image in images),
        "avoid_repetition": True,
        "visual_breaks": count > 1,
    }


def _role(image_type: str, index: int) -> str:
    if image_type == "hero":
        role = "hero"
    elif image_type == "infographic":
        role = "explain"
    elif image_type == "comparison":
        role = "compare"
    elif index > 0:
        role = "illustrate"
    else:
        role = "support"
    if role not in _ROLES:
        raise ValueError(f"Unsupported media role: {role}")
    return role


def _placement(image_type: str) -> str:
    placement = "hero" if image_type == "hero" else "section"
    if placement not in _PLACEMENTS:
        raise ValueError(f"Unsupported media placement: {placement}")
    return placement


def _reason(placement: str, role: str) -> str:
    if placement == "hero":
        return "Use as the article's primary visual anchor."
    return f"Place with the associated section to {role} the section without introducing a separate publishing dependency."


def _strategy_id(lineage: dict[str, str], strategy: dict[str, Any], placements: list[dict[str, Any]]) -> str:
    raw = json.dumps(
        {**lineage, "strategy": strategy, "placements": placements},
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"mediastrategy_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_image_media_strategy(*, image_style: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic, non-networked placement/media strategy from Image Style."""
    _ready(image_style, "image_style_ready", "Image Style")
    lineage = _lineage(image_style)
    styled_images = image_style.get("styled_images")
    if not isinstance(styled_images, list) or not styled_images:
        raise ValueError("Image Style.styled_images must be a non-empty list")

    placements: list[dict[str, Any]] = []
    seen: set[str] = set()
    for image in styled_images:
        if not isinstance(image, dict):
            raise ValueError("Image Style.styled_images entries must be objects")
        image_id = _clean(image.get("image_id"))
        heading = _clean(image.get("section_heading"))
        image_type = _clean(image.get("image_type"))
        section_index = image.get("section_index")
        if not image_id or not heading:
            raise ValueError("Each styled image requires image_id and section_heading")
        if image_id in seen:
            raise ValueError(f"Duplicate styled image_id: {image_id}")
        seen.add(image_id)
        if image_type not in _IMAGE_TYPES:
            raise ValueError(f"Unsupported styled image type: {image_type}")
        if not isinstance(section_index, int) or isinstance(section_index, bool) or section_index < 0:
            raise ValueError("Each styled image requires a non-negative integer section_index")
        placement = _placement(image_type)
        role = _role(image_type, section_index)
        placements.append({
            "image_id": image_id,
            "section_index": section_index,
            "section_heading": heading,
            "placement": placement,
            "media_role": role,
            "reason": _reason(placement, role),
        })

    strategy = _strategy(styled_images)
    return {
        "media_strategy_id": _strategy_id(lineage, strategy, placements),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "image_media_strategy_ready",
        "strategy": strategy,
        "placements": placements,
        "constraints": {
            "network_access": False,
            "provider_call": False,
            "wordpress_write": False,
            "media_upload": False,
            "html_generation": False,
            "source_mutation": False,
        },
        "audit": {
            "method": "image_style_to_media_strategy",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
