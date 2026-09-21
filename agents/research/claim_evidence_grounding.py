from __future__ import annotations

import hashlib
import re
from typing import Any

from .claim_evidence_canonical import meaningful_overlap

METHOD_VERSION = "v2"
_MIN_MEANINGFUL_OVERLAP = 2
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _claim_id(section_index: int, claim_index: int, text: str) -> str:
    digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:12]
    return f"claim_{section_index}_{claim_index}_{digest}"


def _score(sentence: str, record: dict[str, Any]) -> int:
    return len(meaningful_overlap(sentence, record))


def _editorial_score(sentence: str, item: dict[str, Any]) -> int:
    sentence_tokens = {
        token.lower()
        for token in re.findall(r"[a-z0-9]{3,}", sentence)
    }
    source_text = str(item.get("text", "")).lower()
    source_tokens = {
        token.lower()
        for token in re.findall(r"[a-z0-9]{3,}", source_text)
    }
    return len(sentence_tokens & source_tokens)


def ground_claims_by_section(
    *,
    sections: list[dict[str, Any]],
    evidence_records: list[dict[str, Any]],
    editorial_evidence: list[dict[str, Any]] | None = None,
    per_claim: int = 1,
    require_match: bool = True,
) -> list[list[dict[str, Any]]]:
    """Attach canonical Research Evidence refs using page-reviewed source material when available."""
    if per_claim < 1:
        raise ValueError("per_claim must be at least 1")

    global_index = {
        str(record.get("evidence_id", "")).strip(): record
        for record in evidence_records
        if isinstance(record, dict) and str(record.get("evidence_id", "")).strip()
    }
    editorial_index = {
        str(item.get("evidence_id", "")).strip(): item
        for item in (editorial_evidence or [])
        if isinstance(item, dict)
        and str(item.get("evidence_id", "")).strip()
        and str(item.get("status", "")).strip() == "ready"
        and str(item.get("text", "")).strip()
    }

    grounded_sections: list[list[dict[str, Any]]] = []
    for section_index, section in enumerate(sections, start=1):
        section_refs = [str(ref).strip() for ref in section.get("evidence_refs", []) if str(ref).strip()]
        candidates = [global_index[ref] for ref in section_refs if ref in global_index]
        editorial_candidates = [editorial_index[ref] for ref in section_refs if ref in editorial_index]
        sentences = [item.strip() for item in _SENTENCE_SPLIT.split(str(section.get("body", ""))) if item.strip()]
        claims: list[dict[str, Any]] = []

        for claim_index, sentence in enumerate(sentences, start=1):
            if editorial_candidates:
                scored_editorial = sorted(
                    ((item, _editorial_score(sentence, item)) for item in editorial_candidates),
                    key=lambda item: (-item[1], str(item[0].get("evidence_id", ""))),
                )
                selected_editorial = [
                    item for item, score in scored_editorial[:per_claim]
                    if score >= _MIN_MEANINGFUL_OVERLAP
                ]
                selected_refs = [
                    str(item["evidence_id"])
                    for item in selected_editorial
                    if str(item.get("evidence_id", "")).strip() in global_index
                ]
            else:
                scored = sorted(
                    ((record, _score(sentence, record)) for record in candidates),
                    key=lambda item: (-item[1], str(item[0].get("evidence_id", ""))),
                )
                selected_refs = [
                    str(record["evidence_id"])
                    for record, score in scored[:per_claim]
                    if score >= _MIN_MEANINGFUL_OVERLAP
                ]

            status = "grounded" if selected_refs else "blocked"
            if not selected_refs and not require_match and candidates:
                selected_refs = [str(record["evidence_id"]) for record in candidates[:per_claim]]
                status = "provisional"

            claims.append({
                "claim_id": _claim_id(section_index, claim_index, sentence),
                "text": sentence,
                "evidence_refs": selected_refs,
                "grounding_status": status,
            })
        grounded_sections.append(claims)

    return grounded_sections
