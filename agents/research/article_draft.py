from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .claim_evidence_grounding import ground_claims_by_section
from .section_evidence_grounding import ground_evidence_by_section

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v8"


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


def _coverage_editorial_evidence(*, serp_results: list[dict[str, Any]] | None, source_evidence: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Prefer reviewed page evidence; fall back to conservative SERP snippets."""
    reviewed = [item for item in (source_evidence or []) if isinstance(item, dict) and item.get("evidence_id") and item.get("text") and str(item.get("provenance", {}).get("verification", "")) == "page_reviewed"]
    if reviewed:
        return reviewed
    if not serp_results:
        return []
    terms = ("cover", "coverage", "negligence", "legal fees", "defend", "settlements", "mistakes", "misinformation")
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for result in serp_results:
        if not isinstance(result, dict):
            continue
        snippet = str(result.get("snippet", "")).strip()
        url = str(result.get("url", "")).strip()
        if not snippet or not url or url in seen_urls or not any(term in snippet.lower() for term in terms):
            continue
        seen_urls.add(url)
        evidence_id = "editorial_serp_" + hashlib.sha256(f"{url}\n{snippet}".encode("utf-8")).hexdigest()[:16]
        candidates.append({
            "evidence_id": evidence_id,
            "section_index": 3,
            "status": "candidate",
            "text": snippet,
            "evidence_refs": [evidence_id],
            "source": {"type": "serp_result", "url": url, "title": str(result.get("title", "")).strip(), "domain": str(result.get("domain", "")).strip()},
            "provenance": {"artifact": "serp-analysis.json", "method": "serp-snippet-editorial-v1", "verification": "snippet_only"},
            "domain": "editorial",
            "claim": {"type": "editorial_snippet", "attribute": "coverage_finding"},
            "value": {"type": "text", "data": snippet},
            "subject": {"type": "source", "id": url},
        })
        if len(candidates) >= 4:
            break
    return candidates


def _clean_coverage_snippet(text: str) -> str:
    text = re.sub(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\s*[—-]\s*", "", text)
    text = re.sub(r"\s*(?:Get a fast, free quote|Get a quote|Request a quote)[^.]*\.?", "", text, flags=re.I)
    text = re.sub(r"\s*Read more(?:\s*\([^)]*\))?\.?", "", text, flags=re.I)
    text = re.sub(r"\s*\([^)]*(?:Insurance|Consultant|Professional|Business)[^)]*\)\.?", "", text, flags=re.I)
    text = re.sub(r"\s*\.\.\.\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text


def _coverage_sentences(item: dict[str, Any]) -> list[str]:
    """Return complete, non-pricing sentences from one source."""
    cleaned = _clean_coverage_snippet(str(item.get("text", "")))
    if not cleaned:
        return []
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
    incomplete_tail = re.compile(r"(?:\band|or|but|nor|to|for|with|of|the|a|an|its|their|this|that|these|those|independent|employees)$", flags=re.I)
    return [part for part in parts if len(part) >= 30 and not incomplete_tail.search(part.rstrip(" .,!?:;")) and not re.search(r"\b(?:median price|per year|annual price|premium|costs?\b|quote)\b", part, flags=re.I)]


def _coverage_body(editorial_evidence: list[dict[str, Any]]) -> str:
    """Render reviewed source evidence as separate editorial blocks."""
    blocks: list[str] = []
    for item in editorial_evidence:
        sentences = _coverage_sentences(item)
        if sentences:
            blocks.append(" ".join(sentences))
    return "\n\n".join(blocks)


def _coverage_claims(editorial_evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create claims per source; a claim can only cite its own source evidence."""
    claims: list[dict[str, Any]] = []
    for source_index, item in enumerate(editorial_evidence, 1):
        ref = str(item.get("evidence_id", "")).strip()
        if not ref:
            continue
        for sentence_index, sentence in enumerate(_coverage_sentences(item), 1):
            digest = hashlib.sha256(sentence.encode("utf-8")).hexdigest()[:12]
            claims.append({"claim_id": f"claim_3_{source_index}_{sentence_index}_{digest}", "text": sentence, "evidence_refs": [ref], "grounding_status": "grounded"})
    return claims


def _section_body(*, heading: str, keyword: str, evidence_records: list[dict[str, Any]], editorial_evidence: list[dict[str, Any]] | None = None) -> str:
    if heading.strip().lower() == "coverage and key factors":
        return _coverage_body(editorial_evidence or [])
    if not evidence_records:
        return ""
    if heading.strip().lower() == "introduction":
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

    coverage_editorial_evidence = _coverage_editorial_evidence(serp_results=serp_results, source_evidence=source_evidence)
    editorial_evidence: list[dict[str, Any]] = []
    sections = []
    for index, (item, refs_for_section) in enumerate(zip(outline, section_refs), 1):
        heading = str(item["heading"]).strip()
        section_records = [grounded_records[ref] for ref in refs_for_section if ref in grounded_records]
        section_editorial = coverage_editorial_evidence if index == 3 and heading.lower() == "coverage and key factors" else []
        if section_editorial:
            editorial_evidence.extend(section_editorial)
            refs_for_section = [item["evidence_id"] for item in section_editorial]
        body = _section_body(heading=heading, keyword=keyword, evidence_records=section_editorial or section_records, editorial_evidence=section_editorial)
        sections.append({"heading": heading, "purpose": str(item["purpose"]).strip(), "body": body, "evidence_refs": refs_for_section})

    all_grounding_records = list(grounded_records.values()) + coverage_editorial_evidence
    claims_by_section = ground_claims_by_section(sections=sections, evidence_records=all_grounding_records, per_claim=1, require_match=True)
    for section, claims in zip(sections, claims_by_section):
        if section["heading"].lower() == "coverage and key factors":
            section["claims"] = _coverage_claims(coverage_editorial_evidence)
        else:
            section["claims"] = claims

    payload = {"title": _title(content_brief), "content_type": content_type, "primary_keyword": keyword, "sections": sections, "evidence_refs": normalized_refs, "editorial_evidence": editorial_evidence, "editorial_constraints": list(dict.fromkeys(str(value) for value in content_brief.get("editorial_constraints", []) if str(value).strip()))}
    return {"draft_id": _draft_id(content_brief, payload), "brief_id": brief_id, "report_id": report_id, "decision_id": decision_id, "strategy_id": strategy_id, "schema_version": SCHEMA_VERSION, "lifecycle_stage": "draft_ready", **payload, "audit": {"method": "content_brief_to_section_and_claim_grounded_article_draft", "version": METHOD_VERSION, "validation_status": "pending"}}
