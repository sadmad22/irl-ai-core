from __future__ import annotations

import hashlib
import json
from typing import Any

from .claim_evidence_grounding import ground_claims_by_section
from .section_evidence_grounding import ground_evidence_by_section

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v3"


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


def _introduction_body(*, keyword: str, evidence_records: list[dict[str, Any]]) -> str:
    if not evidence_records:
        return ""
    record = evidence_records[0]
    claim = record.get("claim") if isinstance(record.get("claim"), dict) else {}
    value = record.get("value") if isinstance(record.get("value"), dict) else {}
    subject = record.get("subject") if isinstance(record.get("subject"), dict) else {}
    attribute = str(claim.get("attribute") or claim.get("type") or "evidence").replace("_", " ").strip()
    data = value.get("data")
    subject_id = str(subject.get("id") or "the research set").strip()
    if isinstance(data, bool):
        observation = "is supported" if data else "is not supported"
    elif data is None:
        observation = "has been recorded"
    else:
        observation = f"is recorded as {data}"
    return f"This guide focuses on {keyword} and its {attribute} evidence for {subject_id}, where the finding {observation}."


def _coverage_editorial_evidence(*, serp_results: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Build conservative, internal editorial evidence from existing SERP snippets.

    Only snippets that explicitly contain coverage-oriented language are eligible.
    The source URL and artifact provenance are retained. No snippet is treated as
    a verified source document, and an empty result is a safe outcome.
    """
    if not serp_results:
        return []

    terms = (
        "cover",
        "coverage",
        "negligence",
        "legal fees",
        "defend",
        "settlements",
        "mistakes",
        "misinformation",
    )
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for result in serp_results:
        if not isinstance(result, dict):
            continue
        snippet = str(result.get("snippet", "")).strip()
        url = str(result.get("url", "")).strip()
        if not snippet or not url or url in seen_urls:
            continue
        lowered = snippet.lower()
        if not any(term in lowered for term in terms):
            continue
        seen_urls.add(url)
        evidence_id = "editorial_serp_" + hashlib.sha256(f"{url}\n{snippet}".encode("utf-8")).hexdigest()[:16]
        candidates.append({
            "evidence_id": evidence_id,
            "section_index": 3,
            "status": "candidate",
            "text": snippet,
            "evidence_refs": [evidence_id],
            "source": {
                "type": "serp_result",
                "url": url,
                "title": str(result.get("title", "")).strip(),
                "domain": str(result.get("domain", "")).strip(),
            },
            "provenance": {
                "artifact": "serp-analysis.json",
                "method": "serp-snippet-editorial-v1",
                "verification": "snippet_only",
            },
        })
        if len(candidates) >= 4:
            break
    return candidates


def _coverage_body(editorial_evidence: list[dict[str, Any]]) -> str:
    if not editorial_evidence:
        return ""
    parts: list[str] = []
    for item in editorial_evidence:
        text = str(item.get("text", "")).strip()
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        title = str(source.get("title") or source.get("domain") or "a SERP source").strip()
        if text:
            parts.append(f"{text} ({title}).")
    return " ".join(parts)


def _section_body(*, heading: str, keyword: str, evidence_records: list[dict[str, Any]], editorial_evidence: list[dict[str, Any]] | None = None) -> str:
    if heading.strip().lower() == "coverage and key factors":
        return _coverage_body(editorial_evidence or [])
    if not evidence_records:
        return ""
    if heading.strip().lower() == "introduction":
        return _introduction_body(keyword=keyword, evidence_records=evidence_records)
    return " ".join(_evidence_text(record) for record in evidence_records)


def build_article_draft(*, content_brief: dict[str, Any], evidence_records: list[dict[str, Any]] | None = None, serp_results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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

    coverage_editorial_evidence = _coverage_editorial_evidence(serp_results=serp_results)
    editorial_evidence: list[dict[str, Any]] = []
    sections = []
    for index, (item, refs_for_section) in enumerate(zip(outline, section_refs), 1):
        section_records = [grounded_records[ref] for ref in refs_for_section if ref in grounded_records]
        heading = str(item["heading"]).strip()
        section_editorial = coverage_editorial_evidence if index == 3 and heading.lower() == "coverage and key factors" else []
        if section_editorial:
            editorial_evidence.extend(section_editorial)
        body = _section_body(
            heading=heading,
            keyword=keyword,
            evidence_records=section_records,
            editorial_evidence=section_editorial,
        )
        sections.append({
            "heading": heading,
            "purpose": str(item["purpose"]).strip(),
            "body": body,
            "evidence_refs": refs_for_section,
        })

    claims_by_section = ground_claims_by_section(
        sections=sections,
        evidence_records=list(grounded_records.values()),
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
