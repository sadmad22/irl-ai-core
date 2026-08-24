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

    This v2 engine is a quality gate, not a writer, evidence generator, or
    publisher. It accepts the established evidence-grounded contract and the
    newer editorial_evidence/grounded-claim contract.
    """
    ids = {
        k: str(article_draft.get(k, "")).strip()
        for k in ("draft_id", "brief_id", "report_id", "decision_id", "strategy_id")
    }
    if not all(ids.values()):
        raise ValueError("Article Draft lineage identifiers are required")
    if article_draft.get("lifecycle_stage") != "draft_ready":
        raise ValueError("Editorial Review requires a draft_ready Article Draft")

    refs = article_draft.get("evidence_refs")
    sections = article_draft.get("sections")
    findings: list[dict[str, str]] = []

    structure_ok = isinstance(sections, list) and bool(sections) and all(
        isinstance(s, dict)
        and str(s.get("heading", "")).strip()
        and str(s.get("purpose", "")).strip()
        and str(s.get("body", "")).strip()
        for s in sections
    )
    evidence_ok = isinstance(refs, list) and bool(refs) and len(refs) == len(set(str(r) for r in refs))

    def _section_is_grounded(section: dict[str, Any]) -> bool:
        body = str(section.get("body", "")).strip()

        # Preserve the established v1 contract used by existing drafts/tests.
        if "requires editorial verification" in body or "research evidence records" in body:
            return True

        editorial = section.get("editorial_evidence")
        if isinstance(editorial, dict):
            status = str(editorial.get("status", "")).strip().lower()
            section_refs = editorial.get("evidence_refs")
            if status == "ready" and isinstance(section_refs, list) and any(str(ref).strip() for ref in section_refs):
                return True

        claims = section.get("claims")
        if isinstance(claims, list):
            return any(
                isinstance(claim, dict)
                and str(claim.get("grounding_status", "")).strip().lower() == "grounded"
                and str(claim.get("text", "")).strip()
                and isinstance(claim.get("evidence_refs"), list)
                and any(str(ref).strip() for ref in claim.get("evidence_refs", []))
                for claim in claims
            )
        return False

    unsupported_claims_ok = evidence_ok and structure_ok and all(
        _section_is_grounded(s) for s in sections if isinstance(s, dict)
    )
    editorial_ok = bool(str(article_draft.get("title", "")).strip()) and bool(
        str(article_draft.get("primary_keyword", "")).strip()
    )

    if not structure_ok:
        findings.append({"severity": "critical", "category": "structure", "message": "Draft sections are missing required structure."})
    if not evidence_ok:
        findings.append({"severity": "critical", "category": "evidence", "message": "Draft must retain explicit unique evidence_refs."})
    if not unsupported_claims_ok:
        findings.append({"severity": "critical", "category": "unsupported_claims", "message": "Draft contains content that is not grounded in research evidence or marked for editorial verification."})
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
        "evidence_refs": list(dict.fromkeys(str(r) for r in refs if str(r).strip())),
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
