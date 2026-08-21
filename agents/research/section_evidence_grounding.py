from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_SECTION_PROFILES: dict[str, tuple[str, ...]] = {
    "introduction": ("overview", "definition", "intent", "entity", "authority", "serp", "topic"),
    "what_you_need_to_know": ("entity", "market", "intent", "question", "overview", "topic"),
    "coverage_and_key_factors": ("coverage", "benefit", "network", "exclusion", "medical", "claim", "factor"),
    "costs_and_pricing_factors": ("cost", "price", "pricing", "premium", "business", "value", "affiliate"),
    "how_to_compare_options": ("comparison", "compare", "competitor", "provider", "serp", "strategy", "score"),
    "frequently_asked_questions": ("question", "query", "intent", "faq", "answer"),
    "sources_and_editorial_methodology": ("authority", "evidence", "source", "provenance", "audit", "methodology"),
}


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", " ")


def _section_key(section: dict[str, Any]) -> str:
    text = f"{section.get('heading', '')} {section.get('purpose', '')}".lower()
    aliases = (
        ("introduction", "introduction"),
        ("what you need to know", "what_you_need_to_know"),
        ("coverage", "coverage_and_key_factors"),
        ("key factors", "coverage_and_key_factors"),
        ("cost", "costs_and_pricing_factors"),
        ("pricing", "costs_and_pricing_factors"),
        ("compare", "how_to_compare_options"),
        ("frequently asked", "frequently_asked_questions"),
        ("faq", "frequently_asked_questions"),
        ("sources", "sources_and_editorial_methodology"),
        ("methodology", "sources_and_editorial_methodology"),
    )
    for needle, key in aliases:
        if needle in text:
            return key
    return "introduction"


def _record_text(record: dict[str, Any]) -> str:
    claim = record.get("claim") if isinstance(record.get("claim"), dict) else {}
    value = record.get("value") if isinstance(record.get("value"), dict) else {}
    subject = record.get("subject") if isinstance(record.get("subject"), dict) else {}
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    return " ".join(
        _normalize(value) for value in (
            record.get("domain"),
            claim.get("type"),
            claim.get("attribute"),
            subject.get("type"),
            subject.get("id"),
            source.get("artifact"),
        )
    )


def _score(section_key: str, record: dict[str, Any]) -> tuple[int, str]:
    text = _record_text(record)
    score = sum(1 for token in _SECTION_PROFILES.get(section_key, ()) if token in text)
    evidence_id = str(record.get("evidence_id", ""))
    return score, evidence_id


def ground_evidence_by_section(
    *,
    outline: list[dict[str, Any]],
    evidence_refs: list[str],
    evidence_records: list[dict[str, Any]],
    per_section: int = 4,
) -> list[list[str]]:
    """Rank Content Brief evidence_refs independently for each article section.

    Every returned reference is already present in the Content Brief lineage.
    A deterministic fallback keeps every section grounded when its semantic
    profile has no exact match, while still preferring the strongest matches.
    """
    if per_section < 1:
        raise ValueError("per_section must be at least 1")

    ref_set = {str(ref).strip() for ref in evidence_refs if str(ref).strip()}
    indexed = {
        str(record.get("evidence_id", "")).strip(): record
        for record in evidence_records
        if isinstance(record, dict) and str(record.get("evidence_id", "")).strip() in ref_set
    }
    if not indexed:
        return [[] for _ in outline]

    ranked = sorted(
        indexed.values(),
        key=lambda record: (-_score("introduction", record)[0], str(record.get("evidence_id", ""))),
    )
    results: list[list[str]] = []
    for section in outline:
        key = _section_key(section)
        candidates = sorted(
            indexed.values(),
            key=lambda record: (-_score(key, record)[0], str(record.get("evidence_id", ""))),
        )
        selected = candidates[: min(per_section, len(candidates))]
        if not selected:
            selected = ranked[: min(per_section, len(ranked))]
        results.append([str(record["evidence_id"]) for record in selected])
    return results
