from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_CONTENT_TYPES = {"guide", "comparison", "buyer_guide", "article"}

CORE_TRAITS = (
    "calm",
    "confident",
    "clear",
    "practical",
    "evidence_aware",
    "human",
)

BRAND_ARCHETYPE = "trusted_research_advisor"
READER_RELATIONSHIP = "advisor_not_salesperson"


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _ready(document: dict[str, Any], lifecycle: str, label: str) -> None:
    if document.get("lifecycle_stage") != lifecycle:
        raise ValueError(f"Brand Voice requires {lifecycle} {label}")


def _require(document: dict[str, Any], field: str, label: str) -> str:
    value = _clean(document.get(field))
    if not value:
        raise ValueError(f"{label}.{field} is required")
    return value


def _lineage(strategy: dict[str, Any], config: dict[str, Any]) -> dict[str, str]:
    fields = ("report_id", "decision_id", "strategy_id")
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

    result["brief_id"] = _require(config, "brief_id", "Article Configuration")
    result["config_id"] = _require(config, "config_id", "Article Configuration")
    return result


def _definition() -> dict[str, Any]:
    return {
        "identity": {
            "name": "Insurance Review Lab",
            "role": "independent_insurance_research_and_education_platform",
            "archetype": BRAND_ARCHETYPE,
            "reader_relationship": READER_RELATIONSHIP,
        },
        "core_traits": list(CORE_TRAITS),
        "expression_style": {
            "register": "professional_conversational",
            "clarity": "plain_english",
            "structure": "clear_practical_scannable",
            "human_quality": "experienced_human_editor",
        },
        "vocabulary": {
            "preferred": [
                "plain English",
                "precise insurance terminology when necessary",
                "concrete language",
                "reader-friendly explanations",
                "U.S. insurance terminology appropriate to context",
            ],
            "avoid": [
                "unnecessary jargon",
                "buzzwords",
                "marketing clichés",
                "AI-generated clichés",
                "vague corporate language",
                "exaggerated adjectives",
            ],
        },
        "confidence_policy": {
            "principle": "Be confident when evidence supports the statement and qualify material uncertainty.",
            "preferred_qualifiers": [
                "generally",
                "typically",
                "may",
                "can",
                "depending on",
                "varies by insurer/state/policy",
                "based on available information",
            ],
            "prohibited_behavior": "Never manufacture certainty.",
        },
        "editorial_principles": [
            "explain before recommending",
            "compare before concluding",
            "identify trade-offs",
            "distinguish facts from estimates",
            "acknowledge meaningful limitations",
            "prioritize reader usefulness",
            "favor evidence over persuasion",
        ],
        "promotional_boundaries": {
            "position": "non_promotional",
            "avoid": [
                "hard selling",
                "urgency tactics",
                "fear-based messaging",
                "exaggerated claims",
                "unsupported superlatives",
                "guaranteed savings claims",
                "guaranteed coverage claims",
                "manipulative calls to action",
            ],
            "affiliate_neutrality": "Affiliate relationships must not alter editorial tone or conclusions.",
        },
        "insurance_language_rules": [
            "Explain important insurance terminology in plain English.",
            "Distinguish coverage from exclusions.",
            "Distinguish premiums from total potential costs.",
            "Distinguish general information from policy-specific terms.",
            "Acknowledge that pricing and eligibility can vary.",
            "Do not present estimates as universal prices.",
            "Do not imply that one policy is universally appropriate.",
        ],
        "human_writing_rules": [
            "Avoid repetitive sentence structures.",
            "Avoid generic introductions and filler transitions.",
            "Avoid formulaic AI language.",
            "Use natural sentence variation.",
            "Do not add promotional language merely to sound persuasive.",
        ],
        "sentence_paragraph_style": {
            "paragraphs": "concise",
            "voice": "active_where_appropriate",
            "sentence_length": "meaningful_variation",
            "headings": "descriptive",
            "bullets": "use_when_they_improve_scanning",
            "tables": "use_when_comparison_is_genuinely_useful",
            "whitespace": "generous",
        },
        "audience": {
            "primary": "busy U.S. professionals seeking practical insurance guidance",
            "examples": [
                "consultants",
                "accountants",
                "nurses",
                "freelancers",
                "independent professionals",
                "small-business owners",
            ],
            "reader_priorities": [
                "clarity",
                "accuracy",
                "practical usefulness",
                "time efficiency",
            ],
        },
        "mission": "Simplify insurance decisions through clear, practical education and independent, evidence-aware guidance.",
    }


def _id(lineage: dict[str, str], definition: dict[str, Any], article_type: str) -> str:
    payload = {
        **lineage,
        "article_type": article_type,
        "brand_voice": definition,
        "schema_version": SCHEMA_VERSION,
        "method_version": METHOD_VERSION,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"brand_voice_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_brand_voice(*, content_strategy: dict[str, Any], article_config: dict[str, Any]) -> dict[str, Any]:
    """Build the deterministic IRL Brand Voice contract for downstream LLM use."""
    _ready(content_strategy, "content_strategy_ready", "Content Strategy")
    _ready(article_config, "article_config_ready", "Article Configuration")
    lineage = _lineage(content_strategy, article_config)

    strategy_type = _clean(content_strategy.get("content_type"))
    article_type = _clean(article_config.get("article_type"))
    if strategy_type not in _CONTENT_TYPES:
        raise ValueError(f"Unsupported content strategy content_type: {strategy_type}")
    if article_type not in _CONTENT_TYPES:
        raise ValueError(f"Unsupported article type: {article_type}")
    if strategy_type != article_type:
        raise ValueError("Content type and article type must match for Brand Voice")

    definition = _definition()
    return {
        "brand_voice_id": _id(lineage, definition, article_type),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "brand_voice_ready",
        "brand_voice": copy.deepcopy(definition),
        "llm_guidance": {
            "apply_to": ["drafting", "revision", "editorial"],
            "preserve": [
                "meaning",
                "evidence",
                "claim_scope",
                "insurance_qualifications",
            ],
            "do_not_override": [
                "tone_of_voice",
                "point_of_view",
                "source_evidence",
                "article_structure",
            ],
        },
        "constraints": {
            "network_access": False,
            "provider_call": False,
            "llm_invocation": False,
            "source_mutation": False,
        },
        "audit": {
            "method": "irl_brand_voice_semantic_definition",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
