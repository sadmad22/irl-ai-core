from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_INTENTS = {"informational", "commercial", "transactional", "navigational"}
_ARTICLE_TYPES = {"guide", "comparison", "buyer_guide", "article"}


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _ready(document: dict[str, Any], lifecycle: str, label: str) -> None:
    if document.get("lifecycle_stage") != lifecycle:
        raise ValueError(f"Point of View requires {lifecycle} {label}")


def _lineage(strategy: dict[str, Any], config: dict[str, Any]) -> dict[str, str]:
    fields = ("brief_id", "report_id", "decision_id", "strategy_id")
    result: dict[str, str] = {}
    for field in fields:
        strategy_value = _clean(strategy.get(field))
        config_value = _clean(config.get(field))
        if not strategy_value:
            raise ValueError(f"Content Strategy requires {field}")
        if not config_value:
            raise ValueError(f"Article Configuration requires {field}")
        if strategy_value != config_value:
            raise ValueError(f"Lineage mismatch for {field}")
        result[field] = strategy_value
    config_id = _clean(config.get("config_id"))
    if not config_id:
        raise ValueError("Article Configuration.config_id is required")
    return result | {"config_id": config_id}


def _select(intent: str, article_type: str) -> dict[str, str]:
    if article_type == "comparison":
        return {"primary": "third_person", "stance": "editorial_neutral", "pronoun_policy": "avoid_first_person"}
    if article_type in {"guide", "buyer_guide"} or intent in {"informational", "transactional"}:
        return {"primary": "second_person", "stance": "expert_explanatory", "pronoun_policy": "use_you"}
    if intent == "commercial":
        return {"primary": "third_person", "stance": "editorial_neutral", "pronoun_policy": "avoid_first_person"}
    return {"primary": "third_person", "stance": "editorial_neutral", "pronoun_policy": "avoid_first_person"}


def _guidance(pov: dict[str, str]) -> dict[str, list[str]]:
    if pov["primary"] == "second_person":
        preferred = [
            "Address the reader directly when explaining decisions or actions.",
            "Use the reader perspective to make practical guidance explicit.",
            "Keep the expert voice explanatory rather than conversationally personal.",
        ]
        avoid = [
            "Do not imply personal knowledge of the reader's circumstances.",
            "Do not use first-person claims to manufacture authority.",
            "Avoid shifting unpredictably between reader-directed and detached narration.",
        ]
    else:
        preferred = [
            "Describe providers, products, risks, and evidence from an editorially neutral perspective.",
            "Use third-person constructions for comparative or descriptive claims.",
            "Keep evaluative statements tied to stated evidence or methodology.",
        ]
        avoid = [
            "Avoid first-person claims unless explicitly supported by an identified author perspective.",
            "Avoid speaking for the reader or assuming the reader's circumstances.",
            "Avoid promotional language disguised as neutral analysis.",
        ]
    return {
        "preferred_patterns": preferred,
        "avoid_patterns": avoid,
        "consistency_rules": [
            "Maintain the selected point of view throughout the article.",
            "Do not switch perspective solely to strengthen a claim.",
            "Keep point of view separate from tone of voice and brand voice.",
        ],
    }


def _id(lineage: dict[str, str], pov: dict[str, str], guidance: dict[str, Any]) -> str:
    raw = json.dumps({**lineage, "point_of_view": pov, "editorial_guidance": guidance}, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"pov_{digest}"


def build_point_of_view(*, content_strategy: dict[str, Any], article_config: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic point-of-view contract without LLM/network/provider calls."""
    _ready(content_strategy, "content_strategy_ready", "Content Strategy")
    _ready(article_config, "article_config_ready", "Article Configuration")
    lineage = _lineage(content_strategy, article_config)

    intent = _clean(content_strategy.get("intent"))
    article_type = _clean(article_config.get("article_type")) or _clean(content_strategy.get("content_type"))
    if intent and intent not in _INTENTS:
        raise ValueError(f"Unsupported content strategy intent: {intent}")
    if article_type and article_type not in _ARTICLE_TYPES:
        raise ValueError(f"Unsupported article type: {article_type}")

    pov = _select(intent, article_type)
    guidance = _guidance(pov)
    return {
        "point_of_view_id": _id(lineage, pov, guidance),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "point_of_view_ready",
        "point_of_view": pov,
        "editorial_guidance": copy.deepcopy(guidance),
        "constraints": {
            "network_access": False,
            "provider_call": False,
            "tone_of_voice_included": False,
            "brand_voice_included": False,
            "source_mutation": False,
        },
        "audit": {
            "method": "content_strategy_to_point_of_view",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
