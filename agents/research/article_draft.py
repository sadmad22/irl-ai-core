from __future__ import annotations

import hashlib
import json
from typing import Any

from .claim_evidence_grounding import ground_claims_by_section
from .section_evidence_grounding import ground_evidence_by_section

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v4"

_RESEARCH_ONLY_DOMAINS = {"authority", "business"}
_RESEARCH_ONLY_ATTRIBUTES = {
    "authority_score",
    "topic_fit",
    "affiliate_potential",
    "adsense_potential",
    "conversion_potential",
    "commercial_value",
}
_EDITORIAL_ATTRIBUTES = {
    "coverage",
    "provider",
    "cost",
    "price",
    "pricing",
    "premium",
    "risk",
    "claim",
    "exclusion",
    "limit",
    "definition",
    "requirement",
    "eligibility",
}


def _draft_id(brief: dict[str, Any], payload: dict[str, Any]) -> str:
    raw = json.dumps({"brief_id": brief["brief_id"], "payload": payload}, sort_keys=True, ensure_ascii=False)
    return f"draft_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _title(brief: dict[str, Any]) -> str:
    keyword = brief["primary_keyword"]
    content_type = brief["content_type"]
    prefixes = {"guide": "A Practical Guide to", "comparison": "Comparing", "buyer_guide": "How to Choose", "article": "Understanding"}
    return f"{prefixes[content_type]} {keyword.title()}"


def _claim_parts(record: dict[str, Any]) -> tuple[str, Any, str]:
    claim = record.get("claim") if isinstance(record.get("claim"), dict) else {}
    value = record.get("value") if isinstance(record.get("value"), dict) else {}
    subject = record.get("subject") if isinstance(record.get("subject"), dict) else {}
    attribute = str(claim.get("attribute") or claim.get("type") or "evidence").replace("_", " ").strip()
    return attribute, value.get("data"), str(subject.get("id") or "the topic").strip()


def _is_editorial_evidence(record: dict[str, Any]) -> bool:
    domain = str(record.get("domain", "")).strip().lower()
    claim = record.get("claim") if isinstance(record.get("claim"), dict) else {}
    attribute = str(claim.get("attribute", "")).strip().lower()
    if domain in _RESEARCH_ONLY_DOMAINS:
        return False
    if attribute in _RESEARCH_ONLY_ATTRIBUTES:
        return False
    return attribute in _EDITORIAL_ATTRIBUTES


def _evidence_text(record: dict[str, Any]) -> str:
    attribute, data, subject_id = _claim_parts(record)
    if isinstance(data, bool):
        observation = "is supported" if data else "is not supported"
    elif data is None:
        observation = "is identified in the research"
    else:
        observation = f"is recorded as {data}"
    return f"The research identifies {attribute} for {subject_id}; the finding {observation}."


def _introduction_body(*, keyword: str, evidence_records: list[dict[str, Any]]) -> str:
    if not evidence_records:
        return ""
    return _evidence_text(evidence_records[0]).replace("The research identifies", f"This guide examines {keyword}; the research identifies", 1)


def _section_body(*, heading: str, keyword: str, evidence_records: list[dict[str, Any]]) -> str:
    if heading.strip().lower() == "introduction":
        return _introduction_body(keyword=keyword, evidence_records=evidence_records)
    if not evidence_records:
        return ""
    return " ".join(_evidence_text(record) for record in evidence_records)


def _editorial_evidence_entry(section_index: int, refs: list[str]) -> dict[str, Any]:
    return {
        "section_index": section_index,
        "status": "ready" if refs else "insufficient",
        "evidence_refs": list(refs),
    }


def build_article_draft(*, content_brief: dict[str, Any], evidence_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Translate an approved Content Brief into section- and claim-grounded prose."""
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

    normalized_refs = list(dict.fromkeys(str(ref).strip() for ref in refs if str(ref).strip()))
    ref_set = set(normalized_refs)
    indexed_records = {
        str(record.get("evidence_id")).strip(): record
        for record in (evidence_records or [])
        if isinstance(record, dict) and str(record.get("evidence_id", "")).strip()
    }
    grounded_records = {key: indexed_records[key] for key in sorted(ref_set) if key in indexed_records}
    section_refs = ground_evidence_by_section(
        outline=outline,
        evidence_refs=normalized_refs,
        evidence_records=list(grounded_records.values()),
    )

    sections = []
    editorial_evidence = []
    claim_evidence_by_section = []
    for section_index, (item, refs_for_section) in enumerate(zip(outline, section_refs), start=1):
        section_records = [grounded_records[ref] for ref in refs_for_section if ref in grounded_records]
        editorial_records = [record for record in section_records if _is_editorial_evidence(record)]
        editorial_refs = [str(record["evidence_id"]) for record in editorial_records]
        heading = str(item["heading"]).strip()
        body = _section_body(heading=heading, keyword=keyword, evidence_records=editorial_records)
        sections.append({
            "heading": heading,
            "purpose": str(item["purpose"]).strip(),
            "body": body,
            "evidence_refs": refs_for_section,
        })
        editorial_evidence.append(_editorial_evidence_entry(section_index, editorial_refs))
        claim_evidence_by_section.append(editorial_records)

    claims_by_section = ground_claims_by_section(
        sections=sections,
        evidence_records=[record for records in claim_evidence_by_section for record in records],
        per_claim=1,
        require_match=True,
    )
    for section, claims in zip(sections, claims_by_section):
        section["claims"] = claims

    payload = {
        "title": _title(content_brief),
        "content_type": content_type,
        "primary_keyword": keyword,
        "sections": sections,
        "evidence_refs": normalized_refs,
        "editorial_evidence": editorial_evidence,
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
        "audit": {"method": "content_brief_to_section_and_claim_grounded_article_draft", "version": METHOD_VERSION, "validation_status": "pending"},
    }
