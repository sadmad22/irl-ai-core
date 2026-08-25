from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .claim_evidence_grounding import ground_claims_by_section
from .section_evidence_grounding import ground_evidence_by_section

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v12"


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


def _clean_coverage_snippet(text: str) -> str:
    text = re.sub(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\s*[—-]\s*", "", text)
    text = re.sub(r"\s*(?:Get a fast, free quote|Get a quote|Request a quote)[^.]*\.?", "", text, flags=re.I)
    text = re.sub(r"\s*Read more(?:\s*\([^)]*\))?\.?", "", text, flags=re.I)
    text = re.sub(r"\s*\([^)]*(?:Insurance|Consultant|Professional|Business)[^)]*\)\.?", "", text, flags=re.I)
    text = re.sub(r"\s*\.\.\.\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip(" .")


def _coverage_sentences(item: dict[str, Any]) -> list[str]:
    cleaned = _clean_coverage_snippet(str(item.get("text", "")))
    if not cleaned:
        return []
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
    blocked_tail = re.compile(r"(?:\b(?:and|or|to|with|for|of|in|from|the|a|an|as|that|which|employees|independent)\s*)$", re.I)
    return [part for part in parts if len(part) >= 30 and not re.search(r"\b(?:median price|per year|annual price|premium|costs?\b|quote)\b", part, flags=re.I) and not blocked_tail.search(part)]


def _coverage_body(editorial_evidence: list[dict[str, Any]]) -> str:
    sentences: list[str] = []
    seen: set[str] = set()
    for item in editorial_evidence:
        for part in _coverage_sentences(item):
            if part.lower() not in seen:
                sentences.append(part)
                seen.add(part.lower())
    return "\n\n".join(sentences)

def _coverage_claims(
    editorial_evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []

    for item in editorial_evidence:
        sentences = _coverage_sentences(item)

        for sentence in sentences:
            claim_index = len(claims) + 1

            digest = hashlib.sha256(
                f"3:{claim_index}:{sentence}".encode("utf-8")
            ).hexdigest()[:12]

            claims.append(
                {
                    "claim_id": f"claim_3_{claim_index}_{digest}",
                    "text": sentence,
                    "evidence_refs": [
                        str(item["evidence_id"])
                    ],
                    "grounding_status": "grounded",
                }
            )

    return claims

    for source_index, item in enumerate(editorial_evidence, 1):
        for sentence_index, sentence in enumerate(_coverage_sentences(item), 1):
            claim_index = len(claims) + 1

            digest = hashlib.sha256(
                f"3:{claim_index}:{sentence}".encode("utf-8")
            ).hexdigest()[:12]

            claims.append(
                {
                    "claim_id": f"claim_3_{claim_index}_{digest}",
                    "text": sentence,
                    "evidence_refs": [str(item["evidence_id"])],
                    "grounding_status": "grounded",
                }
            )

    return claims

    for source_index, item in enumerate(editorial_evidence, 1):
        for sentence_index, sentence in enumerate(_coverage_sentences(item), 1):
            claim_index = len(claims) + 1
            digest = hashlib.sha256(f"3:{source_index}:{sentence_index}:{sentence}".encode("utf-8")).hexdigest()[:12]
            claims.append({"claim_id": f"claim_3_{source_index}_{sentence_index}_{digest}", "text": sentence, "evidence_refs": [str(item["evidence_id"])], "grounding_status": "grounded"})
    return claims


def _normalize_editorial_evidence(*, item: dict[str, Any], status: str) -> dict[str, Any] | None:
    evidence_id = str(item.get("evidence_id", "")).strip()
    section_index = int(item.get("section_index", 0) or 0)
    text = str(item.get("text", "")).strip()
    source = item.get("source") if isinstance(item.get("source"), dict) else {}
    provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
    url = str(source.get("url", "")).strip()
    verification = str(provenance.get("verification", "")).strip()
    if not evidence_id or section_index < 1 or not text or not url or not verification:
        return None
    return {
        "evidence_id": evidence_id,
        "section_index": section_index,
        "status": status,
        "text": text,
        "source": {
            "type": str(source.get("type", "web_page")),
            "url": url,
            "title": str(source.get("title", "")).strip(),
            "domain": str(source.get("domain") or item.get("domain") or "").strip(),
        },
        "provenance": {
            "artifact": str(provenance.get("artifact", "")).strip(),
            "method": str(provenance.get("method", "")).strip(),
            "verification": verification,
        },
    }


def _page_editorial_evidence(*, section_index: int, source_evidence: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in source_evidence or []:
        if not isinstance(item, dict) or int(item.get("section_index", 0) or 0) != section_index:
            continue
        provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
        if provenance.get("verification") != "page_reviewed":
            continue
        record = _normalize_editorial_evidence(item=item, status="ready")
        if record and record["evidence_id"] not in seen:
            normalized.append(record)
            seen.add(record["evidence_id"])
    return normalized


def _artifact_editorial_evidence(*, section_index: int, source_evidence: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in source_evidence or []:
        if not isinstance(item, dict) or int(item.get("section_index", 0) or 0) != section_index:
            continue
        provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
        if provenance.get("verification") != "artifact_reviewed":
            continue
        record = _normalize_editorial_evidence(item=item, status="ready")
        if record and record["evidence_id"] not in seen:
            normalized.append(record)
            seen.add(record["evidence_id"])
    return normalized


def _page_editorial_body(editorial_evidence: list[dict[str, Any]]) -> str:
    return "\n\n".join(str(item.get("text", "")).strip() for item in editorial_evidence if str(item.get("text", "")).strip())


def _page_editorial_claims(*, section_index: int, editorial_evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for source_index, item in enumerate(editorial_evidence, 1):
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        digest = hashlib.sha256(f"{section_index}:{source_index}:{text}".encode("utf-8")).hexdigest()[:12]
        claims.append({"claim_id": f"claim_{section_index}_{source_index}_{digest}", "text": text, "evidence_refs": [str(item["evidence_id"])], "grounding_status": "grounded"})
    return claims


def _coverage_editorial_evidence(*, serp_results: list[dict[str, Any]] | None, source_evidence: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    page_records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in source_evidence or []:
        if not isinstance(item, dict) or int(item.get("section_index", 0) or 0) != 3:
            continue
        provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
        if provenance.get("verification") != "page_reviewed":
            continue
        record = _normalize_editorial_evidence(item=item, status="ready")
        if record and record["evidence_id"] not in seen:
            page_records.append(record)
            seen.add(record["evidence_id"])
    if page_records:
        return page_records
    for item in serp_results or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("snippet") or item.get("description") or item.get("text") or "").strip()
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        url = str(item.get("url") or source.get("url") or "").strip()
        if not text or not url:
            continue
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        evidence_id = f"editorial_serp_{digest}"
        if evidence_id in seen:
            continue
        record = {
            "evidence_id": evidence_id,
            "section_index": 3,
            "status": "candidate",
            "text": text,
            "source": {"type": "web_page", "url": url, "title": str(item.get("title") or source.get("title") or "").strip(), "domain": str(item.get("domain") or source.get("domain") or "").strip()},
            "provenance": {"artifact": "serp-analysis.json", "method": "serp-snippet-editorial-v1", "verification": "snippet_only"},
        }
        record["source"]["domain"] = record["source"]["domain"] or re.sub(r"^www\.", "", re.sub(r"^https?://", "", url).split("/", 1)[0])
        page_records.append(record)
        seen.add(evidence_id)
    return page_records


def _cost_editorial_evidence(*, source_evidence: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return _page_editorial_evidence(section_index=4, source_evidence=source_evidence)


def _comparison_editorial_evidence(*, source_evidence: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return _page_editorial_evidence(section_index=5, source_evidence=source_evidence)


def _introduction_editorial_evidence(*, source_evidence: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return _page_editorial_evidence(section_index=1, source_evidence=source_evidence)


def _methodology_editorial_evidence(*, source_evidence: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return _artifact_editorial_evidence(section_index=7, source_evidence=source_evidence)


def _section_body(*, heading: str, keyword: str, evidence_records: list[dict[str, Any]], editorial_evidence: list[dict[str, Any]] | None = None) -> str:
    normalized_heading = heading.strip().lower()
    if normalized_heading == "coverage and key factors":
        return _coverage_body(editorial_evidence or [])
    if normalized_heading in {"what you need to know", "costs and pricing factors", "how to compare options", "introduction", "sources and editorial methodology"} and editorial_evidence:
        return _page_editorial_body(editorial_evidence)
    if not evidence_records:
        return ""
    if normalized_heading == "introduction":
        return _introduction_body(keyword=keyword, evidence_records=evidence_records)
    return " ".join(_evidence_text(record) for record in evidence_records)


def build_article_draft(*, content_brief: dict[str, Any], evidence_records: list[dict[str, Any]] | None = None, serp_results: list[dict[str, Any]] | None = None, source_evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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
    indexed_records = {str(record.get("evidence_id")).strip(): record for record in (evidence_records or []) if isinstance(record, dict) and str(record.get("evidence_id", "")).strip()}
    grounded_records = {key: indexed_records[key] for key in sorted(ref_set) if key in indexed_records}
    section_refs = ground_evidence_by_section(outline=outline, evidence_refs=normalized_refs, evidence_records=list(grounded_records.values()))

    introduction_editorial_evidence = _introduction_editorial_evidence(source_evidence=source_evidence)
    coverage_editorial_evidence = _coverage_editorial_evidence(serp_results=serp_results, source_evidence=source_evidence)
    section2_editorial_evidence = _page_editorial_evidence(section_index=2, source_evidence=source_evidence)
    cost_editorial_evidence = _cost_editorial_evidence(source_evidence=source_evidence)
    comparison_editorial_evidence = _comparison_editorial_evidence(source_evidence=source_evidence)
    methodology_editorial_evidence = _methodology_editorial_evidence(source_evidence=source_evidence)
    editorial_evidence: list[dict[str, Any]] = []
    sections = []
    section_evidence_contracts: list[dict[str, Any]] = []

    for index, (item, refs_for_section) in enumerate(zip(outline, section_refs), 1):
        heading = str(item["heading"]).strip()
        section_records = [grounded_records[ref] for ref in refs_for_section if ref in grounded_records]
        normalized_heading = heading.lower()
        if index == 1 and normalized_heading == "introduction":
            section_editorial = introduction_editorial_evidence
        elif index == 2 and normalized_heading == "what you need to know":
            section_editorial = section2_editorial_evidence
        elif index == 3 and normalized_heading == "coverage and key factors":
            section_editorial = coverage_editorial_evidence
        elif index == 4 and normalized_heading == "costs and pricing factors":
            section_editorial = cost_editorial_evidence
        elif index == 5 and normalized_heading == "how to compare options":
            section_editorial = comparison_editorial_evidence
        elif index == 7 and normalized_heading == "sources and editorial methodology":
            section_editorial = methodology_editorial_evidence
        else:
            section_editorial = []
        if section_editorial:
            editorial_evidence.extend(section_editorial)
            refs_for_section = [record["evidence_id"] for record in section_editorial]
        body = _section_body(heading=heading, keyword=keyword, evidence_records=section_editorial or section_records, editorial_evidence=section_editorial)
        sections.append({"heading": heading, "purpose": str(item["purpose"]).strip(), "body": body, "evidence_refs": refs_for_section})
        section_evidence_contracts.append({"section_index": index, "heading": heading, "status": "ready" if section_editorial else "insufficient", "evidence_refs": [record["evidence_id"] for record in section_editorial] if section_editorial else refs_for_section})

    all_grounding_records = list(grounded_records.values()) + introduction_editorial_evidence + coverage_editorial_evidence + section2_editorial_evidence + cost_editorial_evidence + comparison_editorial_evidence + methodology_editorial_evidence
    claims_by_section = ground_claims_by_section(sections=sections, evidence_records=all_grounding_records, per_claim=1, require_match=True)
    for index, (section, claims) in enumerate(zip(sections, claims_by_section), 1):
        normalized_heading = section["heading"].lower()
        if normalized_heading == "coverage and key factors":
            section["claims"] = _coverage_claims(coverage_editorial_evidence)
        elif normalized_heading in {"introduction", "what you need to know", "costs and pricing factors", "how to compare options", "sources and editorial methodology"}:
            if index == 1:
                editorial = introduction_editorial_evidence
            elif index == 2:
                editorial = section2_editorial_evidence
            elif index == 4:
                editorial = cost_editorial_evidence
            elif index == 5:
                editorial = comparison_editorial_evidence
            else:
                editorial = methodology_editorial_evidence
            section["claims"] = _page_editorial_claims(section_index=index, editorial_evidence=editorial) if editorial else claims
        else:
            section["claims"] = claims

    top_level_refs = list(dict.fromkeys(normalized_refs + [str(item["evidence_id"]).strip() for item in editorial_evidence if str(item.get("evidence_id", "")).strip()]))
    payload = {
        "title": _title(content_brief),
        "content_type": content_type,
        "primary_keyword": keyword,
        "sections": sections,
        "evidence_refs": top_level_refs,
        "editorial_evidence": editorial_evidence,
        "section_evidence_contracts": section_evidence_contracts,
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
