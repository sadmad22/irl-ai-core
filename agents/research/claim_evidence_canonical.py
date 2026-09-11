from __future__ import annotations

import re
from typing import Any


_MIN_MEANINGFUL_OVERLAP = 2
_STOPWORDS = {
    "the", "and", "for", "from", "with", "that", "this", "can", "may",
    "are", "is", "was", "were", "has", "have", "had", "will", "would",
    "could", "should", "about", "into", "than", "their", "they", "them",
    "your", "you", "its", "not", "but", "also", "based", "only", "such",
}
_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


def normalize_evidence_value(value: Any) -> str:
    """Normalize a canonical evidence field for deterministic comparison."""
    return str(value or "").strip().lower().replace("_", " ")


def canonical_evidence_text(record: dict[str, Any]) -> str:
    """Return the single canonical reader-independent representation of evidence."""
    claim = record.get("claim") if isinstance(record.get("claim"), dict) else {}
    value = record.get("value") if isinstance(record.get("value"), dict) else {}
    subject = record.get("subject") if isinstance(record.get("subject"), dict) else {}
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    fields = (
        record.get("domain"),
        claim.get("type"),
        claim.get("attribute"),
        value.get("type"),
        value.get("data"),
        subject.get("type"),
        subject.get("id"),
        source.get("artifact"),
    )
    return " ".join(normalize_evidence_value(field) for field in fields)


def canonical_tokens(text: str) -> set[str]:
    """Tokenize canonical evidence and claim text with one deterministic policy."""
    return {token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS}


def meaningful_overlap(claim_text: str, record: dict[str, Any]) -> set[str]:
    """Return meaningful lexical overlap using the canonical evidence representation."""
    return canonical_tokens(claim_text) & canonical_tokens(canonical_evidence_text(record))


def has_meaningful_support(claim_text: str, record: dict[str, Any]) -> bool:
    return len(meaningful_overlap(claim_text, record)) >= _MIN_MEANINGFUL_OVERLAP
