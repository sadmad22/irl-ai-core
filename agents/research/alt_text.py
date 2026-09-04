from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
_MAX_ALT_TEXT_LENGTH = 250
_SPACE_RE = re.compile(r"\s+")


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _required(document: dict[str, Any], field: str, label: str) -> str:
    value = _clean(document.get(field))
    if not value:
        raise ValueError(f"{label}.{field} is required")
    return value


def _ready(document: dict[str, Any], lifecycle: str, label: str) -> None:
    if document.get("lifecycle_stage") != lifecycle:
        raise ValueError(f"Automatic Alt Text requires {lifecycle} {label}")


def _lineage(*documents: dict[str, Any]) -> dict[str, str]:
    fields = ("brief_id", "report_id", "decision_id", "strategy_id")
    result: dict[str, str] = {}
    for field in fields:
        values = {_clean(document.get(field)) for document in documents}
        if "" in values:
            raise ValueError(f"Automatic Alt Text requires {field} in all upstream artifacts")
        if len(values) != 1:
            raise ValueError(f"Automatic Alt Text lineage mismatch for {field}")
        result[field] = values.pop()
    return result


def _normalize(text: str) -> str:
    return _SPACE_RE.sub(" ", text).strip(" .")


def _alt_text(image: dict[str, Any], draft: dict[str, Any], primary: str) -> str:
    heading = _clean(image.get("section_heading"))
    purpose = _clean(image.get("purpose"))
    image_type = _clean(image.get("image_type"))
    title = _clean(draft.get("title"))

    if image_type == "hero":
        base = purpose or f"Illustration related to {primary}"
    elif purpose:
        base = purpose
    else:
        base = f"Illustration for {heading or primary}"

    if heading and heading.casefold() not in base.casefold():
        base = f"{base} Section: {heading}"
    if title and not base:
        base = title

    result = _normalize(base)
    if len(result) > _MAX_ALT_TEXT_LENGTH:
        result = result[:_MAX_ALT_TEXT_LENGTH].rsplit(" ", 1)[0]
    return result or f"Illustration related to {primary}"


def _alt_text_id(lineage: dict[str, str], image_spec_id: str, values: list[dict[str, Any]]) -> str:
    raw = json.dumps(
        {**lineage, "image_spec_id": image_spec_id, "alt_texts": values},
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"alt_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_alt_text_contract(*, image_spec: dict[str, Any], article_draft: dict[str, Any], primary_keyword: str | None = None) -> dict[str, Any]:
    """Build informative alt-text metadata from the image specification and article context."""
    _ready(image_spec, "ai_image_spec_ready", "AI Image Specification")
    _ready(article_draft, "draft_ready", "Article Draft")

    lineage = _lineage(image_spec, article_draft)
    image_spec_id = _required(image_spec, "image_spec_id", "AI Image Specification")
    draft_id = _required(article_draft, "draft_id", "Article Draft")
    primary = _clean(primary_keyword) or _clean(article_draft.get("primary_keyword"))
    if not primary:
        raise ValueError("Automatic Alt Text requires a primary keyword")

    images = image_spec.get("images")
    if not isinstance(images, list) or not images:
        raise ValueError("AI Image Specification.images must be a non-empty list")

    alt_texts: list[dict[str, Any]] = []
    for image in images:
        if not isinstance(image, dict):
            raise ValueError("AI Image Specification.images must contain objects")
        image_id = _required(image, "image_id", "AI Image")
        heading = _required(image, "section_heading", "AI Image")
        section_index = image.get("section_index")
        if isinstance(section_index, bool) or not isinstance(section_index, int) or section_index < 0:
            raise ValueError("AI Image.section_index must be a non-negative integer")
        alt_texts.append(
            {
                "image_id": image_id,
                "section_index": section_index,
                "section_heading": heading,
                "alt_text": _alt_text(image, article_draft, primary),
                "status": "ready",
            }
        )

    alt_texts = copy.deepcopy(alt_texts)
    return {
        "alt_text_id": _alt_text_id(lineage, image_spec_id, alt_texts),
        **lineage,
        "config_id": _required(image_spec, "config_id", "AI Image Specification"),
        "draft_id": draft_id,
        "image_spec_id": image_spec_id,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "alt_text_ready",
        "alt_texts": alt_texts,
        "constraints": {
            "network_access": False,
            "provider_call": False,
            "image_analysis_call": False,
            "keyword_stuffing": False,
            "image_spec_mutation": False,
        },
        "audit": {
            "method": "article_image_context_to_informative_alt_text",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
