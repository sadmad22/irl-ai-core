from __future__ import annotations

import hashlib
import json
from typing import Any

from .section_evidence_grounding import ground_evidence_by_section

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"


def _draft_id(brief: dict[str, Any], payload: dict[str, Any]) -> str:
    raw = json.dumps({"brief_id": brief["brief_id"], "payload": payload}, sort_keys=True, ensure_ascii=False)
    return f"draft_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _title(brief: dict[str, Any]) -> str:
    keyword = brief["primary_keyword"]
    content_type = brief["content_type"]
    prefixes = {"guide": "A Practical Guide to", "comparison": "Comparing", "buyer_guide": "How to Choose", "article": "Understanding"}
    return f"{prefixes[content_type]} {keyword.title()}"


def _evidence_text(record: dict[str, Any]) -> str:
    claim = record.get("claim") if isinstance(record.get("claim"), dict) else {}
    value = record.get("value") if isinstance(record.get("value"), dict) else {}
    subject = record.get("subject") if isinstance(record.get("subject"), dict) else {}
    attribute = str(claim.get("attribute") or claim.get("type") or "observation").replace("_", " ")
    data = value.get("data")
    subject_id = str(subject.get("id") or "the research set")
    if isinstance(data, bool):
        observation = "is supported" if data else "is not supported"
    elif data is None:
        observation = "has been observed"
    else:
        observation = f"has a recorded value of {data}"
    return f"The research evidence records {attribute} for {subject_id}: {observation}."


def _section_body(evidence_records: list[dict[str, Any]]) -> str:
    """Render prose only from explicitly supplied section-level evidence."""
    if not evidence_records:
        return ""
    observations = [_evidence_text(record) for record in evidence_records]
    return " ".join(observations)


def build_article_draft(*, content_brief: dict[str, Any], evidence_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Translate an approved Content Brief into a section-grounded draft."""
    brief_id = str(content_brief.get("brief_id", "")).strip()
    report_id = str(content_brief.get("report_id", "")).strip()
    decision_id = str(content_brief.get("decision_id", "")).strip()
    strategy_id = str(content_brief.get("strategy_id", "")).strip()
    if not all((brief_id, report_id, decision_id, strategy_id)):
        raise ValueError("Content Brief lineage identifiers are required")
    if content_brief.get("lifecycle_stage") != "content_brief_ready":
        raise ValueError("Article Draft requires a content_brief_ready Content Brief")
    refs = content_brief.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        raise ValueError("Content Brief must contain explicit evidence_refs")
    outline = content_brief.get("outline")
    if not isinstance(outline, list) or not outline:
        raise ValueError("Content Brief must contain a non-empty outline")
    content_type = content_brief.get("content_type")
    keyword = str(content_brief.get("primary_keyword", "")).strip()
    if content_type not in {"guide", "comparison", "buyer_guide", "article"}:
        raise ValueError("Content Brief.content_type is invalid")
    if not keyword:
        raise ValueError("Content Brief.primary_keyword is required")

    ref_set = {str(ref).strip() for ref in refs if str(ref).strip()}
    indexed_records = {
        str(record.get("evidence_id")).strip(): record
        for record in (evidence_records or [])
        if isinstance(record, dict) and str(record.get("evidence_id", "")).strip()
    }
    grounded_records = {key: indexed_records[key] for key in sorted(ref_set) if key in indexed_records}
    section_refs = ground_evidence_by_section(
        outline=outline,
        evidence_refs=list(dict.fromkeys(str(ref) for ref in refs if str(ref).strip())),
        evidence_records=list(grounded_records.values()),
    )

    sections = []
    for item, refs_for_section in zip(outline, section_refs):
        section_records = [grounded_records[ref] for ref in refs_for_section if ref in grounded_records]
        sections.append({
            "heading": str(item["heading"]).strip(),
            "purpose": str(item["purpose"]).strip(),
            "body": _section_body(section_records),
            "evidence_refs": refs_for_section,
        })

    payload = {
        "title": _title(content_brief),
        "content_type": content_type,
        "primary_keyword": keyword,
        "sections": sections,
        "evidence_refs": list(dict.fromkeys(str(ref) for ref in refs if str(ref).strip())),
        "editorial_constraints": list(dict.fromkeys(str(value) for value in content_brief.get("editorial_constraints", []) if str(value).strip())),
    }
    return {
        "draft_id": _draft_id(content_brief, payload),
        "brief_id": brief_id,
        "report_id": report_id,
        "decision_id": decision_id,
        "strategy_id": strategy_id,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "draft_ready",
        **payload,
        "audit": {"method": "content_brief_to_section_grounded_article_draft", "version": METHOD_VERSION, "validation_status": "pending"},
    }
