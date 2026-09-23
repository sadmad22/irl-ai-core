from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0"
MAP_VERSION = "v1"


def _claim(claim_type: str, attribute: str, role: str, evidence_kind: str) -> dict[str, str]:
    return {
        "claim_type": claim_type,
        "attribute": attribute,
        "role": role,
        "evidence_kind": evidence_kind,
    }


EXPECTED_CLAIM_MAP: dict[str, dict[str, Any]] = {
    "introduction": {
        "heading": "Introduction",
        "required_claims": [
            _claim("topic_definition", "definition", "required", "substantive"),
            _claim("query_intent", "primary_intent", "required", "substantive"),
        ],
        "supporting_claims": [
            _claim("entity_presence", "mentioned", "supporting", "signal"),
            _claim("entity_classification", "type", "supporting", "signal"),
            _claim("topic_scope", "scope", "supporting", "substantive"),
        ],
        "signal_only": ["query_intent.primary_intent", "serp.position", "business_value.*"],
    },
    "what_you_need_to_know": {
        "heading": "What You Need to Know",
        "required_claims": [
            _claim("topic_definition", "definition", "required", "substantive"),
            _claim("topic_scope", "scope", "required", "substantive"),
            _claim("eligibility", "who_needs_it", "required", "substantive"),
            _claim("use_case", "primary_use", "required", "substantive"),
        ],
        "supporting_claims": [
            _claim("risk_factor", "risk", "supporting", "substantive"),
            _claim("entity_presence", "mentioned", "supporting", "signal"),
            _claim("question", "frequency", "supporting", "signal"),
        ],
        "signal_only": ["question_frequency.count", "entity_presence.mentioned", "authority.authority_score"],
    },
    "coverage_and_key_factors": {
        "heading": "Coverage and Key Factors",
        "required_claims": [
            _claim("coverage_fact", "coverage", "required", "substantive"),
            _claim("coverage_fact", "benefit", "required", "substantive"),
            _claim("exclusion_fact", "exclusion", "required", "substantive"),
        ],
        "supporting_claims": [
            _claim("network_fact", "network", "supporting", "substantive"),
            _claim("requirement_fact", "requirement", "supporting", "substantive"),
            _claim("limitation_fact", "limitation", "supporting", "substantive"),
            _claim("claim_process_fact", "claim_process", "supporting", "substantive"),
        ],
        "signal_only": ["entity_presence.mentioned", "query_intent.primary_intent", "business_value.*"],
    },
    "costs_and_pricing_factors": {
        "heading": "Costs and Pricing Factors",
        "required_claims": [
            _claim("pricing_fact", "premium", "required", "substantive"),
            _claim("pricing_factor", "cost_driver", "required", "substantive"),
            _claim("pricing_factor", "price_variable", "required", "substantive"),
        ],
        "supporting_claims": [
            _claim("pricing_fact", "cost_range", "supporting", "substantive"),
            _claim("pricing_fact", "deductible", "supporting", "substantive"),
            _claim("pricing_fact", "limit_effect", "supporting", "substantive"),
            _claim("pricing_fact", "coverage_effect", "supporting", "substantive"),
        ],
        "signal_only": ["business_value.*", "cpc", "search_volume"],
    },
    "how_to_compare_options": {
        "heading": "How to Compare Options",
        "required_claims": [
            _claim("comparison_fact", "criterion", "required", "substantive"),
            _claim("option_attribute", "coverage_difference", "required", "substantive"),
            _claim("option_attribute", "cost_difference", "required", "substantive"),
        ],
        "supporting_claims": [
            _claim("provider_presence", "mentioned", "supporting", "signal"),
            _claim("network_fact", "network_difference", "supporting", "substantive"),
            _claim("exclusion_fact", "exclusion_difference", "supporting", "substantive"),
            _claim("service_fact", "service_difference", "supporting", "substantive"),
        ],
        "signal_only": ["serp.rank", "authority.authority_score", "business_value.*"],
    },
    "frequently_asked_questions": {
        "heading": "Frequently Asked Questions",
        "required_claims": [
            _claim("question_fact", "question", "required", "substantive"),
            _claim("answer_fact", "answer", "required", "substantive"),
        ],
        "supporting_claims": [
            _claim("question_frequency", "count", "supporting", "signal"),
            _claim("intent", "question_intent", "supporting", "signal"),
            _claim("coverage_fact", "faq_topic", "supporting", "substantive"),
            _claim("cost_fact", "faq_topic", "supporting", "substantive"),
        ],
        "signal_only": ["question_frequency.count"],
    },
    "sources_and_editorial_methodology": {
        "heading": "Sources and Editorial Methodology",
        "required_claims": [
            _claim("source_identity", "source", "required", "substantive"),
            _claim("provenance_fact", "method", "required", "substantive"),
            _claim("lineage_fact", "evidence_lineage", "required", "substantive"),
        ],
        "supporting_claims": [
            _claim("source_identity", "provider", "supporting", "substantive"),
            _claim("provenance_fact", "analyzer", "supporting", "substantive"),
            _claim("provenance_fact", "analyzer_version", "supporting", "substantive"),
            _claim("evidence_status", "status", "supporting", "substantive"),
        ],
        "signal_only": ["authority.authority_score"],
    },
}


def expected_claims_for(section_key: str) -> dict[str, Any] | None:
    item = EXPECTED_CLAIM_MAP.get(section_key)
    return item.copy() if item is not None else None


def claim_ref(item: dict[str, str]) -> dict[str, str]:
    return {"claim_type": item["claim_type"], "attribute": item["attribute"]}
