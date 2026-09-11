from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v2"


def _review_id(draft_id: str, payload: dict[str, Any]) -> str:
    raw = json.dumps({"draft_id": draft_id, "payload": payload}, sort_keys=True, ensure_ascii=False)
    return f"review_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_editorial_review(*, article_draft: dict[str, Any]) -> dict[str, Any]:
    """Run deterministic structural/editorial gates over an Article Draft.

    This v2 engine evaluates reader-facing prose through the Article Draft's
    canonical claim-grounding results. It does not accept internal research
    serialization as evidence that prose is grounded.
    """
    keys = ("draft_id", "brief_id", "report_id", "decision_id", "strategy_id")
    ids = {key: str(article_draft.get(key, "")).strip() for key in keys}
    if not all(ids.values()):
        raise ValueError("Article Draft lineage identifiers are required")
    if article_draft.get("lifecycle_stage") != "draft_ready":
        raise ValueError("Editorial Review requires a draft_ready Article Draft")

    refs = article_draft.get("evidence_refs")
    sections = article_draft.get("sections")
    findings: list[dict[str, str]] = []

    structure_ok = isinstance(sections, list) and bool(sections) and all(
        isinstance(section, dict)
        and str(section.get("heading", "")).strip()
        and str(section.get("purpose", "")).strip()
        and str(section.get("body", "")).strip()
        for section in sections
    )
    evidence_ok = isinstance(refs, list) and bool(refs) and len(refs) == len(set(str(ref) for ref in refs))

    def _claims_are_grounded(section: dict[str, Any]) -> bool:
        claims = section.get("claims")
        if not isinstance(claims, list) or not claims:
            return False
        for claim in claims:
            if not isinstance(claim, dict):
                return False
            if not str(claim.get("text", "")).strip():
                return False
            claim_refs = [str(ref).strip() for ref in claim.get("evidence_refs", []) if str(ref).strip()]
            if str(claim.get("grounding_status", "")) != "grounded" or not claim_refs:
                return False
        return True

    unsupported_claims_ok = evidence_ok and structure_ok and all(
        _claims_are_grounded(section) for section in sections if isinstance(section, dict)
    )
    editorial_ok = bool(str(article_draft.get("title", "")).strip()) and bool(
        str(article_draft.get("primary_keyword", "")).strip()
    )

    if not structure_ok:
        findings.append({"severity": "critical", "category": "structure", "message": "Draft sections are missing required structure."})
    if not evidence_ok:
        findings.append({"severity": "critical", "category": "evidence", "message": "Draft must retain explicit unique evidence_refs."})
    if not unsupported_claims_ok:
        findings.append({"severity": "critical", "category": "unsupported_claims", "message": "Every reader-facing factual claim must have grounded evidence_refs."})
    if not editorial_ok:
        findings.append({"severity": "critical", "category": "editorial", "message": "Draft title and primary keyword are required."})

    checks = {
        "structure": structure_ok,
        "evidence_coverage": evidence_ok,
        "unsupported_claims": unsupported_claims_ok,
        "editorial_compliance": editorial_ok,
    }
    outcome = "approved" if all(checks.values()) else "needs_revision"
    if any(f["severity"] == "critical" for f in findings) and not structure_ok:
        outcome = "rejected"

    payload = {
        "outcome": outcome,
        "checks": checks,
        "evidence_refs": list(dict.fromkeys(str(ref) for ref in refs if str(ref).strip())),
        "findings": findings,
    }
    return {
        "review_id": _review_id(ids["draft_id"], payload),
        **ids,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "editorial_review_ready",
        **payload,
        "audit": {"method": "article_draft_editorial_review", "version": METHOD_VERSION, "validation_status": "validated"},
    }
