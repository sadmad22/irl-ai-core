from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_INTENT = {"informational", "commercial", "transactional", "navigational"}
_CONTENT_TYPES = {"guide", "comparison", "buyer_guide", "article"}


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _ready(document: dict[str, Any], lifecycle: str, label: str) -> None:
    if document.get("lifecycle_stage") != lifecycle:
        raise ValueError(f"Tone of Voice requires {lifecycle} {label}")


def _require(document: dict[str, Any], field: str, label: str) -> Any:
    if field not in document:
        raise ValueError(f"{label}.{field} is required")
    return document[field]


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
        if config_value != strategy_value:
            raise ValueError(f"Lineage mismatch for {field}")
        result[field] = strategy_value
    config_id = _clean(_require(config, "config_id", "Article Configuration"))
    return result | {"config_id": config_id}


def _select_primary(intent: str, article_type: str) -> str:
    if article_type == "comparison":
        return "analytical"
    if article_type == "buyer_guide" or intent in {"commercial", "transactional"}:
        return "authoritative"
    if article_type == "guide" or intent == "informational":
        return "educational"
    return "professional"


def _tone(primary: str) -> dict[str, str]:
    profiles = {
        "educational": {"formality": "professional", "directness": "direct", "warmth": "moderate", "technicality": "moderate"},
        "analytical": {"formality": "professional", "directness": "direct", "warmth": "low", "technicality": "technical"},
        "authoritative": {"formality": "professional", "directness": "direct", "warmth": "low", "technicality": "moderate"},
        "professional": {"formality": "professional", "directness": "balanced", "warmth": "moderate", "technicality": "moderate"},
        "conversational": {"formality": "conversational", "directness": "balanced", "warmth": "high", "technicality": "plain"},
        "reassuring": {"formality": "professional", "directness": "gentle", "warmth": "high", "technicality": "plain"},
    }
    return {"primary": primary, **profiles[primary]}


def _guidance(primary: str) -> dict[str, Any]:
    preferred = {
        "educational": ["clear", "explanatory", "evidence-aware", "practical"],
        "analytical": ["precise", "evidence-aware", "comparative", "structured"],
        "authoritative": ["confident", "precise", "evidence-aware", "decisive"],
        "professional": ["clear", "credible", "practical", "measured"],
        "conversational": ["clear", "accessible", "natural", "helpful"],
        "reassuring": ["clear", "calm", "supportive", "measured"],
    }[primary]
    return {
        "preferred_traits": preferred,
        "avoid_traits": ["hype", "sensationalism", "fear-based language", "unsupported certainty"],
        "sentence_guidance": [
            "Prefer active voice.",
            "Keep sentences clear and information-dense.",
            "Explain specialized insurance terms when first introduced.",
            "Use concrete language over promotional phrasing.",
        ],
        "reader_address": "you",
    }


def _id(lineage: dict[str, str], tone: dict[str, Any], guidance: dict[str, Any]) -> str:
    raw = json.dumps({**lineage, "tone": tone, "editorial_guidance": guidance}, sort_keys=True, separators=(",", ":"))
    return f"tone_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_tone_of_voice(*, content_strategy: dict[str, Any], article_config: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic editorial tone contract without LLM/network/provider calls."""
    _ready(content_strategy, "content_strategy_ready", "Content Strategy")
    _ready(article_config, "article_config_ready", "Article Configuration")
    lineage = _lineage(content_strategy, article_config)

    intent = _clean(content_strategy.get("intent"))
    article_type = _clean(article_config.get("article_type")) or _clean(content_strategy.get("content_type"))
    if intent and intent not in _INTENT:
        raise ValueError(f"Unsupported content strategy intent: {intent}")
    if article_type and article_type not in _CONTENT_TYPES:
        raise ValueError(f"Unsupported article type: {article_type}")

    primary = _select_primary(intent, article_type)
    tone = _tone(primary)
    guidance = _guidance(primary)

    return {
        "tone_of_voice_id": _id(lineage, tone, guidance),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "tone_of_voice_ready",
        "tone": tone,
        "editorial_guidance": copy.deepcopy(guidance),
        "constraints": {
            "network_access": False,
            "provider_call": False,
            "brand_voice_included": False,
            "point_of_view_included": False,
            "source_mutation": False,
        },
        "audit": {
            "method": "content_strategy_to_tone_of_voice",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
