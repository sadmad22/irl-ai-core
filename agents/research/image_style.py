from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_BRAND = "Insurance Review Lab"
_VISUAL_LANGUAGE = ["professional", "editorial", "research-oriented", "clean", "modern", "trustworthy"]
_COMPOSITION = ["clear focal point", "structured composition", "generous whitespace", "restrained visual hierarchy"]
_ILLUSTRATION = ["premium editorial illustration", "clean geometric elements", "subtle analytical/data motifs"]
_RESTRICTIONS = ["no watermark", "no unnecessary text", "no logos", "no visual clutter", "no off-brand colors", "no misleading imagery"]
_COLORS = {"deep_navy": "#0F172A", "modern_blue": "#2563EB", "cyan_accent": "#06B6D4", "white": "#FFFFFF"}


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _require_ready(document: dict[str, Any]) -> None:
    if document.get("lifecycle_stage") != "ai_image_spec_ready":
        raise ValueError("Image Style requires a ai_image_spec_ready AI Image Specification")


def _lineage(document: dict[str, Any]) -> dict[str, str]:
    fields = ("brief_id", "report_id", "decision_id", "strategy_id", "config_id", "draft_id", "image_spec_id")
    values = {field: _clean(document.get(field)) for field in fields}
    missing = next((field for field, value in values.items() if not value), None)
    if missing:
        raise ValueError(f"Image Style requires {missing} in AI Image Specification")
    return values


def _style() -> dict[str, Any]:
    return {
        "brand": _BRAND,
        "color_palette": copy.deepcopy(_COLORS),
        "visual_language": list(_VISUAL_LANGUAGE),
        "composition": list(_COMPOSITION),
        "illustration_direction": list(_ILLUSTRATION),
        "restrictions": list(_RESTRICTIONS),
    }


def _styled_prompt(prompt: str) -> str:
    base = _clean(prompt)
    if not base:
        raise ValueError("AI Image Specification image.prompt is required")
    palette = ", ".join(_COLORS.values())
    language = ", ".join(_VISUAL_LANGUAGE)
    composition = ", ".join(_COMPOSITION)
    illustration = ", ".join(_ILLUSTRATION)
    restrictions = ", ".join(_RESTRICTIONS)
    return (
        f"{base} Apply {_BRAND} visual style: {language}. "
        f"Use the brand palette {palette}. "
        f"Composition: {composition}. "
        f"Illustration direction: {illustration}. "
        f"Restrictions: {restrictions}."
    )


def _image_style_id(lineage: dict[str, str], styled_images: list[dict[str, Any]]) -> str:
    raw = json.dumps({**lineage, "visual_style": _style(), "styled_images": styled_images}, sort_keys=True, separators=(",", ":"))
    return f"imgstyle_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_image_style(*, ai_image_spec: dict[str, Any]) -> dict[str, Any]:
    """Apply the deterministic IRL brand visual style contract without generating images."""
    _require_ready(ai_image_spec)
    lineage = _lineage(ai_image_spec)
    images = ai_image_spec.get("images")
    if not isinstance(images, list) or not images:
        raise ValueError("AI Image Specification.images must be a non-empty list")

    styled_images: list[dict[str, Any]] = []
    for image in images:
        if not isinstance(image, dict):
            raise ValueError("AI Image Specification.images must contain objects")
        image_id = _clean(image.get("image_id"))
        heading = _clean(image.get("section_heading"))
        prompt = _clean(image.get("prompt"))
        image_type = _clean(image.get("image_type"))
        if not image_id or not heading or not prompt or not image_type:
            raise ValueError("Each AI Image Specification image requires image_id, image_type, section_heading, and prompt")
        section_index = image.get("section_index")
        if not isinstance(section_index, int) or isinstance(section_index, bool) or section_index < 0:
            raise ValueError("Each AI Image Specification image requires a valid section_index")
        if image_type not in {"hero", "section", "infographic", "comparison"}:
            raise ValueError("AI Image Specification contains an unsupported image_type")
        styled_images.append({
            "image_id": image_id,
            "section_index": section_index,
            "section_heading": heading,
            "image_type": image_type,
            "styled_prompt": _styled_prompt(prompt),
        })

    image_style_id = _image_style_id(lineage, styled_images)
    return {
        "image_style_id": image_style_id,
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "image_style_ready",
        "visual_style": _style(),
        "styled_images": copy.deepcopy(styled_images),
        "constraints": {
            "network_access": False,
            "provider_call": False,
            "image_analysis_call": False,
            "media_strategy_included": False,
            "source_mutation": False,
        },
        "audit": {
            "method": "ai_image_spec_to_brand_visual_style",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
