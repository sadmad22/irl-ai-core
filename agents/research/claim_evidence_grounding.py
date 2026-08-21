from __future__ import annotations

import hashlib
import re
from typing import Any


METHOD_VERSION = "v1"
_MIN_MEANINGFUL_OVERLAP = 2
_STOPWORDS = {
    "the", "and", "for", "from", "with", "that", "this", "can", "may",
    "are", "is", "was", "were", "has", "have", "had", "will", "would",
    "could", "should", "about", "into", "than", "their", "they", "them",
    "your", "you", "its", "not", "but", "also", "based", "only", "such",
}
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", " ")


def _claim_id(section_index: int, claim_index: int, text: str) -> str:
    digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:12]
    return f"claim_{section_index}_{claim_index}_{digest}"


def _record_text(record: dict[str, Any]) -> str:
    claim = record.get("claim") if isinstance(record.get("claim"), dict) else {}
    value = record.get("value") if isinstance(record.get("value"), dict) else {}
    subject = record.get("subject") if isinstance(record.get("subject"), dict) else {}
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    return " ".join(
        _normalize(value)
        for value in (
            record.get("domain"),
            claim.get("type"),
            claim.get("attribute"),
            value.get("type"),
            value.get("data"),
            subject.get("type"),
            subject.get("id"),
            source.get("artifact"),
        )
    )


def _sentence_tokens(sentence: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]{3,}", sentence.lower())
        if token not in _STOPWORDS
    }


def _score(sentence: str, record: dict[str, Any]) -> int:
    return len(_sentence_tokens(sentence) & _sentence_tokens(_record_text(record)))


def ground_claims_by_section(
    *,
    sections: list[dict[str, Any]],
    evidence_records: list[dict[str, Any]],
    per_claim: int = 1,
    require_match: bool = True,
) -> list[list[dict[str, Any]]]:
    """Attach deterministic evidence refs to individual factual sentences.

    Only evidence records already assigned to the section are eligible. A
    claim needs meaningful lexical support from its eligible evidence before
    it can be marked grounded. Weak overlap on generic words is insufficient.
    Claims without support are blocked rather than assigned invented evidence.
    """
    if per_claim < 1:
        raise ValueError("per_claim must be at least 1")

    global_index = {
        str(record.get("evidence_id", "")).strip(): record
        for record in evidence_records
        if isinstance(record, dict) and str(record.get("evidence_id", "")).strip()
    }
    grounded_sections: list[list[dict[str, Any]]] = []

    for section_index, section in enumerate(sections, start=1):
        section_refs = [str(ref).strip() for ref in section.get("evidence_refs", []) if str(ref).strip()]
        candidates = [global_index[ref] for ref in section_refs if ref in global_index]
        sentences = [item.strip() for item in _SENTENCE_SPLIT.split(str(section.get("body", ""))) if item.strip()]
        claims: list[dict[str, Any]] = []

        for claim_index, sentence in enumerate(sentences, start=1):
            scored = sorted(
                ((record, _score(sentence, record)) for record in candidates),
                key=lambda item: (-item[1], str(item[0].get("evidence_id", ""))),
            )
            selected = [
                record
                for record, score in scored[:per_claim]
                if score >= _MIN_MEANINGFUL_OVERLAP
            ]
            status = "grounded" if selected else "blocked"
            if not selected and not require_match and candidates:
                selected = candidates[:per_claim]
                status = "provisional"

            claims.append({
                "claim_id": _claim_id(section_index, claim_index, sentence),
                "text": sentence,
                "evidence_refs": [str(record["evidence_id"]) for record in selected],
                "grounding_status": status,
            })

        grounded_sections.append(claims)

    return grounded_sections
