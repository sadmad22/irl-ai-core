from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_STOPWORDS = {
    "about", "after", "again", "also", "among", "because", "before", "being",
    "between", "could", "does", "from", "have", "into", "more", "most", "other",
    "should", "some", "than", "that", "their", "there", "these", "they", "this",
    "through", "under", "what", "when", "where", "which", "while", "with", "would",
    "your", "insurance", "health", "plan", "plans", "coverage", "option", "options",
}
_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS}


def _evidence_text(record: dict[str, Any]) -> str:
    claim = record.get("claim") if isinstance(record.get("claim"), dict) else {}
    value = record.get("value") if isinstance(record.get("value"), dict) else {}
    subject = record.get("subject") if isinstance(record.get("subject"), dict) else {}
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    return " ".join(
        str(value).strip()
        for value in (
            record.get("domain", ""),
            claim.get("type", ""),
            claim.get("attribute", ""),
            value.get("data", ""),
            subject.get("id", ""),
            source.get("artifact", ""),
        )
    )


def _audit_id(claim_id: str, result: str, refs: list[str]) -> str:
    raw = json.dumps({"claim_id": claim_id, "result": result, "evidence_refs": refs}, sort_keys=True)
    return f"claim_audit_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def audit_claim(*, claim: dict[str, Any], evidence_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify a claim using only its assigned evidence records.

    This is a deterministic evidence sufficiency audit, not an LLM truth oracle.
    ``supported`` requires grounded status, assigned evidence, and meaningful
    lexical overlap. ``disputed`` is reserved for explicit contradictory evidence.
    """
    claim_id = str(claim.get("claim_id", "")).strip()
    text = str(claim.get("text", "")).strip()
    refs = [str(ref).strip() for ref in claim.get("evidence_refs", []) if str(ref).strip()]
    index = {str(record.get("evidence_id", "")).strip(): record for record in evidence_records if record.get("evidence_id")}
    selected = [index[ref] for ref in refs if ref in index]

    contradictory = [record for record in selected if str(record.get("relation", "")).strip().lower() in {"contradicts", "refutes"}]
    overlap = max((_tokens(text) & _tokens(_evidence_text(record)) for record in selected), key=len, default=set())

    if contradictory:
        result = "disputed"
        reason = "Assigned evidence explicitly contradicts the claim."
    elif str(claim.get("grounding_status", "")) != "grounded" or not selected:
        result = "insufficient"
        reason = "Claim is not grounded by usable assigned evidence."
    elif len(overlap) < 2:
        result = "insufficient"
        reason = "Assigned evidence does not provide enough lexical support for the claim."
    else:
        result = "supported"
        reason = "Assigned evidence provides sufficient deterministic lexical support."

    return {
        "audit_id": _audit_id(claim_id, result, refs),
        "claim_id": claim_id,
        "result": result,
        "evidence_refs": refs,
        "matched_tokens": sorted(overlap),
        "reason": reason,
    }


def audit_article_claims(*, article_draft: dict[str, Any], evidence_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit every Article Draft claim and fail closed on insufficient support."""
    evidence_index = {str(record.get("evidence_id", "")).strip(): record for record in evidence_records if record.get("evidence_id")}
    audits: list[dict[str, Any]] = []
    for section in article_draft.get("sections", []):
        for claim in section.get("claims", []) if isinstance(section, dict) else []:
            refs = [str(ref).strip() for ref in claim.get("evidence_refs", []) if str(ref).strip()]
            audits.append(audit_claim(claim=claim, evidence_records=[evidence_index[ref] for ref in refs if ref in evidence_index]))

    counts = {status: sum(1 for item in audits if item["result"] == status) for status in ("supported", "disputed", "insufficient")}
    outcome = "passed" if audits and counts["supported"] == len(audits) else "needs_revision"
    summary = {
        "total_claims": len(audits),
        "supported": counts["supported"],
        "disputed": counts["disputed"],
        "insufficient": counts["insufficient"],
    }
    return {
        "audit_id": _audit_id(str(article_draft.get("draft_id", "")), outcome, [item["audit_id"] for item in audits]),
        "draft_id": str(article_draft.get("draft_id", "")).strip(),
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "claim_audit_ready",
        "outcome": outcome,
        "summary": summary,
        "counts": counts,
        "claims": audits,
        "audit": {"method": "claim_audit_validator", "version": METHOD_VERSION, "validation_status": "validated"},
    }
