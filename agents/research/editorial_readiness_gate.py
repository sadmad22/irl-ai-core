from __future__ import annotations

from typing import Any

from .article_draft_quality import validate_article_draft_quality

TARGET_STAGE = "wordpress_draft_ready"
FAIL_STAGE = "needs_revision"

_REQUIRED_HEADINGS = (
    "Introduction",
    "What You Need to Know",
    "Coverage and Key Factors",
    "Costs and Pricing Factors",
    "How to Compare Options",
    "Frequently Asked Questions",
    "Sources and Editorial Methodology",
)


def _section_readiness(article_draft: dict[str, Any]) -> tuple[bool, list[str]]:
    sections = article_draft.get("sections")
    contracts = article_draft.get("section_evidence_contracts")
    errors: list[str] = []

    if not isinstance(sections, list) or [str(s.get("heading", "")) for s in sections if isinstance(s, dict)] != list(_REQUIRED_HEADINGS):
        errors.append("required seven-section structure is incomplete or out of order")
        return False, errors

    contract_by_index = {
        int(c.get("section_index", 0) or 0): c
        for c in contracts
        if isinstance(c, dict) and int(c.get("section_index", 0) or 0) > 0
    } if isinstance(contracts, list) else {}

    for index, section in enumerate(sections, 1):
        if not str(section.get("body", "")).strip():
            errors.append(f"section_{index}:empty_body")
        refs = section.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"section_{index}:missing_evidence_refs")
        claims = section.get("claims")
        if not isinstance(claims, list) or not claims:
            errors.append(f"section_{index}:missing_claims")
        contract = contract_by_index.get(index)
        if not contract or contract.get("status") != "ready":
            errors.append(f"section_{index}:evidence_contract_not_ready")

    return not errors, errors


def _editorial_source_readiness(article_draft: dict[str, Any]) -> tuple[bool, list[str]]:
    evidence = article_draft.get("editorial_evidence")
    if not isinstance(evidence, list) or not evidence:
        return False, ["missing editorial_evidence"]

    by_id = {str(item.get("evidence_id", "")): item for item in evidence if isinstance(item, dict) and str(item.get("evidence_id", "")).strip()}
    errors: list[str] = []

    for section_index in range(1, 7):
        section = article_draft["sections"][section_index - 1]
        for ref in section.get("evidence_refs", []):
            item = by_id.get(str(ref))
            if item is None:
                errors.append(f"section_{section_index}:missing_editorial_evidence:{ref}")
            elif str(item.get("provenance", {}).get("verification", "")) != "page_reviewed":
                errors.append(f"section_{section_index}:non_page_reviewed_evidence:{ref}")

    method_section = article_draft["sections"][6]
    for ref in method_section.get("evidence_refs", []):
        item = by_id.get(str(ref))
        if item is None:
            errors.append(f"section_7:missing_editorial_evidence:{ref}")
        elif str(item.get("provenance", {}).get("verification", "")) != "artifact_reviewed":
            errors.append(f"section_7:methodology_evidence_must_be_artifact_reviewed:{ref}")

    return not errors, errors


def evaluate_editorial_readiness(*, article_draft: dict[str, Any]) -> dict[str, Any]:
    """Fail-safe final gate. Never mutates the draft and never publishes to WordPress."""
    quality = validate_article_draft_quality(article_draft=article_draft)
    section_ok, section_errors = _section_readiness(article_draft)
    source_ok, source_errors = _editorial_source_readiness(article_draft) if section_ok else (False, ["section readiness failed"])

    checks = {
        "article_draft_quality": quality.get("outcome") == "passed",
        "seven_section_readiness": section_ok,
        "editorial_source_readiness": source_ok,
    }
    findings: list[dict[str, str]] = []
    findings.extend({"severity": "critical", "category": "section_readiness", "message": error} for error in section_errors)
    findings.extend({"severity": "critical", "category": "editorial_source_readiness", "message": error} for error in source_errors)
    findings.extend(quality.get("findings", []))

    passed = all(checks.values())
    return {
        "outcome": "passed" if passed else "needs_revision",
        "target_lifecycle_stage": TARGET_STAGE if passed else FAIL_STAGE,
        "publish_allowed": False,
        "wordpress_write_allowed": False,
        "draft_id": str(article_draft.get("draft_id", "")).strip(),
        "checks": checks,
        "findings": findings,
        "quality": quality,
        "audit": {
            "method": "article_editorial_readiness_gate",
            "version": "v1",
            "validation_status": "validated",
        },
    }
