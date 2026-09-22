from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Callable

SCHEMA_VERSION = "1.1"
METHOD_VERSION = "v2"

_PROVIDER_KEYS = {"sections", "tables", "images"}
_REQUIRED_IMAGE_FIELDS = {"image_id", "section_index", "placement", "prompt", "alt_text", "evidence_refs"}
_REQUIRED_TABLE_FIELDS = {"table_id", "title", "section_index", "columns", "rows", "evidence_refs"}
_LEAKAGE_MARKERS = (
    "the research evidence records",
    "evidence_id",
    "subject_id",
    "claim.attribute",
    "raw evidence",
)


class ArticleWriterLLMProviderProtocol:
    def write(self, *, sections: list[dict[str, Any]], editorial_rules: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _require_ready(brief: dict[str, Any]) -> None:
    if brief.get("lifecycle_stage") != "content_brief_ready":
        raise ValueError("Article Writer requires a content_brief_ready Content Brief")


def _provider_result(provider: Any, sections: list[dict[str, Any]], rules: dict[str, Any], content_type: str) -> dict[str, Any]:
    if provider is None:
        raise ValueError("Article Writer requires an explicitly injected LLM provider")
    writer: Callable[..., Any] | None = getattr(provider, "write", None)
    if writer is None or not callable(writer):
        raise ValueError("Article Writer LLM provider must expose write(sections=..., editorial_rules=...)")
    result = writer(sections=copy.deepcopy(sections), editorial_rules=copy.deepcopy(rules))
    if not isinstance(result, dict) or set(result) != _PROVIDER_KEYS:
        raise ValueError("Article Writer provider must return exactly sections, tables, and images")

    returned_sections = result["sections"]
    if not isinstance(returned_sections, list) or len(returned_sections) != len(sections):
        raise ValueError("Article Writer provider must return exactly one section per input section")
    expected_indexes = list(range(len(sections)))
    seen: list[int] = []
    for item in returned_sections:
        if not isinstance(item, dict) or set(item) != {"section_index", "body"}:
            raise ValueError("Article Writer provider sections must contain only section_index and body")
        index = item["section_index"]
        body = _text(item.get("body"))
        if isinstance(index, bool) or not isinstance(index, int) or index not in expected_indexes or not body:
            raise ValueError("Article Writer section_index/body is invalid")
        if any(marker in body.lower() for marker in _LEAKAGE_MARKERS):
            raise ValueError("Article Writer output contains internal research metadata")
        seen.append(index)
    if sorted(seen) != expected_indexes:
        raise ValueError("Article Writer provider section indexes must match the input sections")

    tables = result["tables"]
    if not isinstance(tables, list):
        raise ValueError("Article Writer tables must be an array")
    table_ids: set[str] = set()
    for table in tables:
        if not isinstance(table, dict) or set(table) != _REQUIRED_TABLE_FIELDS:
            raise ValueError("Article Writer table has an unsupported shape")
        table_id = _text(table.get("table_id"))
        title = _text(table.get("title"))
        section_index = table.get("section_index")
        columns = table.get("columns")
        rows = table.get("rows")
        evidence_refs = table.get("evidence_refs")
        if not table_id or table_id in table_ids or not title:
            raise ValueError("Article Writer table_id/title is invalid or duplicated")
        if isinstance(section_index, bool) or not isinstance(section_index, int) or section_index not in expected_indexes:
            raise ValueError("Article Writer table section_index is invalid")
        if not isinstance(columns, list) or not columns or not all(_text(value) for value in columns):
            raise ValueError("Article Writer table columns must be a non-empty string array")
        if not isinstance(rows, list) or not rows:
            raise ValueError("Article Writer tables must contain at least one row")
        for row in rows:
            if not isinstance(row, list) or len(row) != len(columns) or not all(_text(value) for value in row):
                raise ValueError("Article Writer table rows must match the column count")
        if not isinstance(evidence_refs, list) or not evidence_refs or len(set(evidence_refs)) != len(evidence_refs):
            raise ValueError("Article Writer table evidence_refs must be a unique non-empty array")
        table_ids.add(table_id)

    if content_type in {"comparison", "buyer_guide"} and not tables:
        raise ValueError("Comparison and buyer-guide drafts require at least one structured table")

    images = result["images"]
    if not isinstance(images, list) or not images:
        raise ValueError("Article Writer requires at least one image specification")
    image_ids: set[str] = set()
    for image in images:
        if not isinstance(image, dict) or set(image) != _REQUIRED_IMAGE_FIELDS:
            raise ValueError("Article Writer image has an unsupported shape")
        image_id = _text(image.get("image_id"))
        placement = _text(image.get("placement"))
        prompt = _text(image.get("prompt"))
        alt_text = _text(image.get("alt_text"))
        section_index = image.get("section_index")
        evidence_refs = image.get("evidence_refs")
        if not image_id or image_id in image_ids or not placement or not prompt or not alt_text:
            raise ValueError("Article Writer image specification is incomplete or duplicated")
        if isinstance(section_index, bool) or not isinstance(section_index, int) or section_index not in expected_indexes:
            raise ValueError("Article Writer image section_index is invalid")
        if not isinstance(evidence_refs, list) or len(set(evidence_refs)) != len(evidence_refs):
            raise ValueError("Article Writer image evidence_refs must be a unique array")
        image_ids.add(image_id)

    return copy.deepcopy(result)


def _draft_id(brief: dict[str, Any], payload: dict[str, Any]) -> str:
    raw = json.dumps({"brief_id": brief["brief_id"], "payload": payload}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"draft_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def write_article_draft(
    *,
    content_brief: dict[str, Any],
    section_evidence: list[dict[str, Any]],
    llm_provider: Any,
) -> dict[str, Any]:
    """Convert an approved Content Brief and grounded source material into draft assets."""
    _require_ready(content_brief)
    content_type = _text(content_brief.get("content_type"))
    if content_type not in {"guide", "comparison", "buyer_guide", "article"}:
        raise ValueError("Content Brief.content_type is invalid")
    outline = content_brief.get("outline")
    if not isinstance(outline, list) or not outline:
        raise ValueError("Content Brief must contain a non-empty outline")
    if not isinstance(section_evidence, list) or len(section_evidence) != len(outline):
        raise ValueError("Article Writer requires one grounded evidence package per outline section")

    provider_sections = []
    for index, (item, evidence) in enumerate(zip(outline, section_evidence)):
        if not isinstance(item, dict) or not isinstance(evidence, dict):
            raise ValueError("Article Writer section inputs must be objects")
        heading = _text(item.get("heading"))
        purpose = _text(item.get("purpose"))
        refs = evidence.get("evidence_refs")
        records = evidence.get("evidence_records")
        editorial = evidence.get("editorial_evidence", [])
        if not heading or not purpose or not isinstance(refs, list) or not refs or not isinstance(records, list):
            raise ValueError("Article Writer section evidence package is incomplete")
        if not isinstance(editorial, list):
            raise ValueError("Article Writer editorial_evidence must be an array")
        provider_sections.append({
            "section_index": index,
            "heading": heading,
            "purpose": purpose,
            "evidence_refs": list(dict.fromkeys(str(ref).strip() for ref in refs if str(ref).strip())),
            "evidence_records": copy.deepcopy(records),
            "editorial_evidence": copy.deepcopy(editorial),
        })

    rules = {
        "reader_facing_prose": True,
        "use_evidence_as_source_material_not_visible_metadata": True,
        "use_page_reviewed_editorial_evidence_when_available": True,
        "preserve_claim_meaning": True,
        "no_new_facts": True,
        "no_internal_ids_or_research_metadata_in_prose": True,
        "evidence_constrained_prose": True,
        "factual_claims_must_be_supported_by_assigned_evidence": True,
        "do_not_use_unassigned_evidence": True,
        "omit_or_reframe_unsupported_factual_statements": True,
        "avoid_broad_unsourced_generalizations": True,
        "heading_is_external": True,
        "evidence_constrained_writing_instructions": (
            "Write each section only from the evidence assigned to that section. "
            "For every factual or externally verifiable statement, use information "
            "directly supported by the assigned evidence records or available "
            "page-reviewed editorial evidence. Do not introduce facts, figures, "
            "provider details, coverage details, costs, comparisons, statistics, "
            "or recommendations from general knowledge or from evidence assigned "
            "to another section. If the assigned evidence does not support a factual "
            "statement, omit it or narrow/reframe it so that it does not make an "
            "unsupported factual claim. Prefer precise evidence-supported statements "
            "over broad unsourced generalizations. Use concise reader-facing "
            "transitions where needed, but do not add unsupported factual content. "
            "The section heading is supplied externally and must not be generated."
        ),
        "tables_are_structured_and_evidence_linked": True,
        "images_are_specs_only_until_media_generation": True,
    }
    provider_result = _provider_result(llm_provider, provider_sections, rules, content_type)
    source_by_index = {section["section_index"]: section for section in provider_sections}
    sections = []
    for item in sorted(provider_result["sections"], key=lambda value: value["section_index"]):
        source = source_by_index[item["section_index"]]
        sections.append({
            "heading": source["heading"],
            "purpose": source["purpose"],
            "body": item["body"],
            "evidence_refs": source["evidence_refs"],
        })

    payload = {
        "title": f"{content_type.replace('_', ' ').title()}: {str(content_brief['primary_keyword']).title()}",
        "content_type": content_type,
        "primary_keyword": str(content_brief["primary_keyword"]).strip(),
        "sections": sections,
        "tables": provider_result["tables"],
        "images": provider_result["images"],
        "evidence_refs": list(dict.fromkeys(str(ref).strip() for ref in content_brief["evidence_refs"] if str(ref).strip())),
        "editorial_evidence": [
            item
            for section in provider_sections
            for item in section["editorial_evidence"]
            if isinstance(item, dict)
        ],
        "editorial_constraints": list(dict.fromkeys(str(value) for value in content_brief.get("editorial_constraints", []) if str(value).strip())),
    }
    return {
        "draft_id": _draft_id(content_brief, payload),
        "brief_id": str(content_brief["brief_id"]),
        "report_id": str(content_brief["report_id"]),
        "decision_id": str(content_brief["decision_id"]),
        "strategy_id": str(content_brief["strategy_id"]),
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "draft_ready",
        **payload,
        "audit": {
            "method": "content_brief_to_injected_llm_article_writer_and_grounding",
            "version": METHOD_VERSION,
            "validation_status": "pending",
        },
    }
