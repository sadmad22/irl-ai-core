from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"


def _review_id(draft_id: str, payload: dict[str, Any]) -> str:
    raw = json.dumps({"draft_id": draft_id, "payload": payload}, sort_keys=True, ensure_ascii=False)
    return f"review_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_editorial_review(*, article_draft: dict[str, Any]) -> dict[str, Any]:
    """Run deterministic structural/editorial gates over an Article Draft.

    This v1 engine is a quality gate, not a writer, evidence generator, or
    publisher. It only evaluates the draft against invariants already present
    in the upstream artifacts.
    """
    ids = {k: str(article_draft.get(k, "")).strip() for k in ("draft_id", "brief_id", "report_id", "decision_id", "strategy_id")}
    if not all(ids.values()):
        raise ValueError("Article Draft lineage identifiers are required")
    if article_draft.get("lifecycle_stage") != "draft_ready":
        raise ValueError("Editorial Review requires a draft_ready Article Draft")

    refs = article_draft.get("evidence_refs")
    sections = article_draft.get("sections")
    findings: list[dict[str, str]] = []

    structure_ok = isinstance(sections, list) and bool(sections) and all(
        isinstance(s, dict) and str(s.get("heading", "")).strip() and str(s.get("purpose", "")).strip() and str(s.get("body", "")).strip()
        for s in sections
    )
    evidence_ok = isinstance(refs, list) and bool(refs) and len(refs) == len(set(str(r) for r in refs))
    unsupported_claims_ok = evidence_ok and all("requires editorial verification" in str(s.get("body", "")) for s in sections if isinstance(s, dict))
    editorial_ok = bool(str(article_draft.get("title", "")).strip()) and bool(str(article_draft.get("primary_keyword", "")).strip())

    if not structure_ok:
        findings.append({"severity":"critical","category":"structure","message":"Draft sections are missing required structure."})
    if not evidence_ok:
        findings.append({"severity":"critical","category":"evidence","message":"Draft must retain explicit unique evidence_refs."})
    if not unsupported_claims_ok:
        findings.append({"severity":"critical","category":"unsupported_claims","message":"Draft contains content that is not marked for editorial verification."})
    if not editorial_ok:
        findings.append({"severity":"critical","category":"editorial","message":"Draft title and primary keyword are required."})

    checks = {
        "structure": structure_ok,
        "evidence_coverage": evidence_ok,
        "unsupported_claims": unsupported_claims_ok,
        "editorial_compliance": editorial_ok,
    }
    outcome = "approved" if all(checks.values()) else "needs_revision"
    if any(f["severity"] == "critical" for f in findings) and not structure_ok:
        outcome = "rejected"

    payload = {"outcome": outcome, "checks": checks, "evidence_refs": list(dict.fromkeys(str(r) for r in refs if str(r).strip())), "findings": findings}
    return {
        "review_id": _review_id(ids["draft_id"], payload),
        **ids,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "editorial_review_ready",
        **payload,
        "audit": {"method":"article_draft_editorial_review","version":METHOD_VERSION,"validation_status":"validated"},
    }
