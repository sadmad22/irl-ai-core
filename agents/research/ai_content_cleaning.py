from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Callable

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_CHANGE_CATEGORIES = {"grammar", "clarity", "redundancy", "formatting", "ai_artifact"}
_RISK_FLAGS = {"claim_change", "new_fact", "citation_change", "structural_change", "meaning_change"}
_PROVIDER_KEYS = {"status", "sections", "changes", "risk_flags"}


class EditorialCleanupLLMProviderProtocol:
    """Documentation-only provider shape for an injected editorial cleanup LLM."""

    def clean(self, *, sections: list[dict[str, Any]], editorial_rules: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _require_ready(document: dict[str, Any], lifecycle: str, label: str) -> None:
    if document.get("lifecycle_stage") != lifecycle:
        raise ValueError(f"AI Content Cleaning requires {lifecycle} {label}")


def _lineage(draft: dict[str, Any]) -> dict[str, str]:
    fields = ("draft_id", "brief_id", "report_id", "decision_id", "strategy_id")
    result: dict[str, str] = {}
    for field in fields:
        value = _text(draft.get(field))
        if not value:
            raise ValueError(f"Article Draft requires {field}")
        result[field] = value
    return result


def _input_sections(draft: dict[str, Any]) -> list[dict[str, Any]]:
    sections = draft.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("Article Draft.sections is required and must be non-empty")
    result: list[dict[str, Any]] = []
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            raise ValueError("Article Draft sections must be objects")
        heading = _text(section.get("heading"))
        body = _text(section.get("body"))
        if not heading or not body:
            raise ValueError("Each Article Draft section requires non-empty heading and body")
        result.append({"section_index": index, "heading": heading, "body": body})
    return result


def _editorial_rules(tone_of_voice: dict[str, Any] | None, point_of_view: dict[str, Any] | None) -> dict[str, Any]:
    rules: dict[str, Any] = {
        "preserve_claims": True,
        "preserve_evidence_and_citations": True,
        "preserve_section_structure": True,
        "add_new_facts": False,
        "rewrite_only_for_editorial_quality": True,
    }
    if tone_of_voice is not None:
        _require_ready(tone_of_voice, "tone_of_voice_ready", "Tone of Voice")
        rules["tone_of_voice_id"] = _text(tone_of_voice.get("tone_of_voice_id"))
        if not rules["tone_of_voice_id"]:
            raise ValueError("Tone of Voice requires tone_of_voice_id")
    if point_of_view is not None:
        _require_ready(point_of_view, "point_of_view_ready", "Point of View")
        rules["point_of_view_id"] = _text(point_of_view.get("point_of_view_id"))
        if not rules["point_of_view_id"]:
            raise ValueError("Point of View requires point_of_view_id")
    return rules


def _provider_result(provider: Any, sections: list[dict[str, Any]], rules: dict[str, Any]) -> dict[str, Any]:
    if provider is None:
        raise ValueError("AI Content Cleaning requires an explicitly injected LLM provider")
    cleaner: Callable[..., Any] | None = getattr(provider, "clean", None)
    if cleaner is None or not callable(cleaner):
        raise ValueError("AI Content Cleaning LLM provider must expose clean(sections=..., editorial_rules=...)")
    result = cleaner(sections=copy.deepcopy(sections), editorial_rules=copy.deepcopy(rules))
    if not isinstance(result, dict):
        raise ValueError("AI Content Cleaning LLM provider must return an object")
    unknown = set(result) - _PROVIDER_KEYS
    if unknown:
        raise ValueError(f"Unsupported AI Content Cleaning provider fields: {sorted(unknown)}")
    status = _text(result.get("status"))
    if status not in {"cleaned", "unchanged", "needs_review"}:
        raise ValueError("Unsupported AI Content Cleaning provider status")
    returned_sections = result.get("sections")
    if not isinstance(returned_sections, list) or len(returned_sections) != len(sections):
        raise ValueError("AI Content Cleaning provider must return exactly one section per input section")
    expected_indexes = list(range(len(sections)))
    seen: list[int] = []
    for item in returned_sections:
        if not isinstance(item, dict) or set(item) != {"section_index", "cleaned_body"}:
            raise ValueError("AI Content Cleaning provider sections must contain only section_index and cleaned_body")
        index = item["section_index"]
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError("AI Content Cleaning section_index must be a non-negative integer")
        body = _text(item.get("cleaned_body"))
        if not body:
            raise ValueError("AI Content Cleaning cleaned_body must be non-empty")
        seen.append(index)
    if sorted(seen) != expected_indexes:
        raise ValueError("AI Content Cleaning provider section indexes must match the input sections")
    changes = result.get("changes", [])
    if not isinstance(changes, list):
        raise ValueError("AI Content Cleaning changes must be an array")
    for change in changes:
        if not isinstance(change, dict) or set(change) != {"section_index", "category", "description"}:
            raise ValueError("AI Content Cleaning changes have an unsupported shape")
        if isinstance(change["section_index"], bool) or not isinstance(change["section_index"], int) or change["section_index"] not in expected_indexes:
            raise ValueError("AI Content Cleaning change section_index is invalid")
        if change["category"] not in _CHANGE_CATEGORIES or not _text(change["description"]):
            raise ValueError("AI Content Cleaning change category or description is invalid")
    risk_flags = result.get("risk_flags", [])
    if not isinstance(risk_flags, list) or not all(isinstance(flag, str) and flag in _RISK_FLAGS for flag in risk_flags) or len(set(risk_flags)) != len(risk_flags):
        raise ValueError("AI Content Cleaning risk_flags must be a unique array of supported values")
    if risk_flags:
        status = "needs_review"
    return {"status": status, "sections": copy.deepcopy(returned_sections), "changes": copy.deepcopy(changes), "risk_flags": copy.deepcopy(risk_flags)}


def _id(lineage: dict[str, str], sections: list[dict[str, Any]], provider_result: dict[str, Any]) -> str:
    raw = json.dumps({"lineage": lineage, "sections": sections, "provider_result": provider_result}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"editorial_cleanup_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_ai_content_cleaning(*, article_draft: dict[str, Any], llm_provider: Any, tone_of_voice: dict[str, Any] | None = None, point_of_view: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build an editorial-cleanup contract without mutating the source draft."""
    _require_ready(article_draft, "draft_ready", "Article Draft")
    lineage = _lineage(article_draft)
    sections = _input_sections(article_draft)
    rules = _editorial_rules(tone_of_voice, point_of_view)
    provider_result = _provider_result(llm_provider, sections, rules)
    cleaned_sections = []
    source_by_index = {section["section_index"]: section for section in sections}
    for item in provider_result["sections"]:
        source = source_by_index[item["section_index"]]
        cleaned_sections.append({
            "section_index": source["section_index"],
            "heading": source["heading"],
            "original_body": source["body"],
            "cleaned_body": item["cleaned_body"],
        })
    cleaned_sections.sort(key=lambda item: item["section_index"])
    output = {
        "editorial_cleanup_id": _id(lineage, cleaned_sections, provider_result),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "editorial_cleanup_ready",
        "status": provider_result["status"],
        "cleaned_sections": cleaned_sections,
        "changes": provider_result["changes"],
        "risk_flags": provider_result["risk_flags"],
        "constraints": {
            "network_access": False,
            "provider_call": True,
            "source_mutation": False,
            "draft_mutation": False,
            "new_facts": False,
            "claim_rewriting": False,
            "structure_rewriting": False,
        },
        "audit": {
            "method": "injected_llm_editorial_cleanup",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
    return output
