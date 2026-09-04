from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_IMAGE_TYPES = {"hero", "section", "infographic", "comparison"}
_BRAND = "Insurance Review Lab"

_VISUAL_STYLE = {
    "brand": _BRAND,
    "palette": {
        "deep_navy": "#0F172A",
        "modern_blue": "#2563EB",
        "cyan_accent": "#06B6D4",
        "white": "#FFFFFF",
    },
    "visual_language": ["professional", "editorial", "research-oriented", "clean", "modern", "trustworthy"],
    "composition": ["clear focal point", "structured composition", "generous whitespace", "restrained visual hierarchy"],
    "illustration_direction": ["premium editorial illustration", "clean geometric elements", "subtle analytical/data motifs"],
    "restrictions": ["no watermark", "no unnecessary text", "no logos", "no visual clutter", "no off-brand colors", "no misleading imagery"],
}


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _require(document: dict[str, Any], field: str, label: str) -> Any:
    if field not in document:
        raise ValueError(f"{label}.{field} is required")
    return document[field]


def _require_ready(document: dict[str, Any], lifecycle: str, label: str) -> None:
    if document.get("lifecycle_stage") != lifecycle:
        raise ValueError(f"Image Style requires a {lifecycle} {label}")


def _lineage(document: dict[str, Any]) -> dict[str, str]:
    fields = ("brief_id", "report_id", "decision_id", "strategy_id", "config_id", "draft_id", "image_spec_id")
    result: dict[str, str] = {}
    for field in fields:
        value = _clean(document.get(field))
        if not value:
            raise ValueError(f"Image Style requires {field} in AI Image Specification")
        result[field] = value
    return result


def _style_prompt(prompt: str) -> str:
    style = (
        " Apply Insurance Review Lab brand visual direction: professional editorial research aesthetic; "
        "Deep Navy #0F172A, Modern Blue #2563EB, Cyan Accent #06B6D4, and White #FFFFFF; "
        "premium editorial illustration, clean geometric elements, subtle analytical/data motifs, "
        "clear focal point, structured composition, generous whitespace, restrained visual hierarchy. "
        "No watermark, unnecessary text, logos, visual clutter, off-brand colors, or misleading imagery."
    )
    return f"{prompt.strip()}{style}" if prompt.strip() else style.strip()


def _image_style_id(lineage: dict[str, str], styled_images: list[dict[str, Any]]) -> str:
    raw = json.dumps({**lineage, "styled_images": styled_images, "visual_style": _VISUAL_STYLE}, sort_keys=True, separators=(",", ":"))
    return f"imgstyle_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_image_style(*, ai_image_spec: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic, non-networked brand visual style artifact from AI Image Specification."""
    _require_ready(ai_image_spec, "ai_image_spec_ready", "AI Image Specification")
    lineage = _lineage(ai_image_spec)
    images = _require(ai_image_spec, "images", "AI Image Specification")
    if not isinstance(images, list) or not images:
        raise ValueError("AI Image Specification.images must be a non-empty list")

    styled_images: list[dict[str, Any]] = []
    for image in images:
        if not isinstance(image, dict):
            raise ValueError("AI Image Specification.images entries must be objects")
        image_id = _clean(image.get("image_id"))
        image_type = _clean(image.get("image_type"))
        heading = _clean(image.get("section_heading"))
        prompt = _clean(image.get("prompt"))
        section_index = image.get("section_index")
        if not image_id or not heading or not prompt:
            raise ValueError("Each AI image requires image_id, section_heading, and prompt")
        if image_type not in _IMAGE_TYPES:
            raise ValueError(f"Unsupported AI image type: {image_type}")
        if not isinstance(section_index, int) or section_index < 0:
            raise ValueError("Each AI image requires a non-negative integer section_index")
        styled_images.append({
            "image_id": image_id,
            "section_index": section_index,
            "section_heading": heading,
            "image_type": image_type,
            "styled_prompt": _style_prompt(prompt),
        })

    return {
        "image_style_id": _image_style_id(lineage, styled_images),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "image_style_ready",
        "visual_style": copy.deepcopy(_VISUAL_STYLE),
        "styled_images": styled_images,
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
