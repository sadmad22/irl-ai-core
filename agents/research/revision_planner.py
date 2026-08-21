from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v2"

_SECTION_RE = re.compile(r"section_(\d+)")
_CLAIM_RE = re.compile(r"claim_(\d+)_([0-9]+)(?:_[a-z0-9]+)?")
_QUALITY_CLAIM_RE = re.compile(r"claim_(\d+)(?=[_:])")


def _plan_id(*, gate: str, action: str, target: dict[str, Any], reason: str) -> str:
    raw = json.dumps(
        {"gate": gate, "action": action, "target": target, "reason": reason},
        sort_keys=True,
        ensure_ascii=False,
    )
    return f"revision_plan_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _target_from_text(text: str) -> dict[str, Any]:
    target: dict[str, Any] = {}
    section = _SECTION_RE.search(text)
    claim = _CLAIM_RE.search(text)
    if section:
        target["section_index"] = int(section.group(1))
    if claim:
        target["claim_id"] = claim.group(0)
    else:
        quality_claim = _QUALITY_CLAIM_RE.search(text)
        if quality_claim:
            target["claim_id"] = quality_claim.group(0)
    return target


def _claim_lookup(article_draft: dict[str, Any]) -> dict[str, dict[str, Any]]:
    claims: dict[str, dict[str, Any]] = {}
    for section in article_draft.get("sections", []):
        if not isinstance(section, dict):
            continue
        for claim in section.get("claims", []):
            if isinstance(claim, dict) and str(claim.get("claim_id", "")).strip():
                claims[str(claim["claim_id"]).strip()] = claim
    return claims


def _add_plan(
    plans: list[dict[str, Any]],
    *,
    gate: str,
    action: str,
    target: dict[str, Any],
    reason: str,
    evidence_refs: list[str] | None = None,
    rerun_gates: list[str] | None = None,
) -> None:
    evidence_refs = list(dict.fromkeys(str(ref).strip() for ref in (evidence_refs or []) if str(ref).strip()))
    rerun_gates = list(dict.fromkeys(rerun_gates or []))
    plan = {
        "plan_id": _plan_id(gate=gate, action=action, target=target, reason=reason),
        "priority": "critical" if gate in {"article_draft_quality", "claim_audit"} else "high",
        "gate": gate,
        "action": action,
        "target": target,
        "reason": reason,
        "evidence_refs": evidence_refs,
        "rerun_gates": rerun_gates,
    }
    if plan["plan_id"] not in {item["plan_id"] for item in plans}:
        plans.append(plan)


def build_revision_plan(*, result: dict[str, Any]) -> dict[str, Any]:
    """Diagnose the first blocking gate and produce targeted, executable revision work."""
    plans: list[dict[str, Any]] = []
    draft = result.get("article_draft", {}) if isinstance(result.get("article_draft"), dict) else {}
    claims = _claim_lookup(draft)

    quality = result.get("article_draft_quality", {})
    if quality.get("outcome") != "passed":
        findings = quality.get("findings", [])
        for finding in findings if isinstance(findings, list) else []:
            if not isinstance(finding, dict):
                continue
            category = str(finding.get("category", "article_draft")).strip()
            message = str(finding.get("message", "Article Draft Quality requires revision.")).strip()
            target = _target_from_text(message)
            action = "revise_claim" if category in {"claim_evidence_grounding", "claim_quality"} else "revise_article_draft"
            refs: list[str] = []
            claim_id = target.get("claim_id")
            if claim_id and claim_id in claims:
                refs = [str(ref) for ref in claims[claim_id].get("evidence_refs", [])]
            _add_plan(
                plans,
                gate="article_draft_quality",
                action=action,
                target=target,
                reason=message,
                evidence_refs=refs,
                rerun_gates=["article_draft_quality", "claim_quality", "claim_audit"],
            )
        if not plans:
            _add_plan(
                plans,
                gate="article_draft_quality",
                action="revise_article_draft",
                target={},
                reason="Article Draft Quality requires revision.",
                rerun_gates=["article_draft_quality", "claim_quality", "claim_audit"],
            )
    else:
        audit = result.get("claim_audit", {})
        if audit.get("outcome") != "passed":
            for item in audit.get("claims", []) if isinstance(audit.get("claims"), list) else []:
                if not isinstance(item, dict) or item.get("result") == "supported":
                    continue
                claim_id = str(item.get("claim_id", "")).strip()
                target = {"claim_id": claim_id} if claim_id else {}
                claim = claims.get(claim_id, {})
                section_index = next(
                    (
                        index
                        for index, section in enumerate(draft.get("sections", []), start=1)
                        if any(isinstance(c, dict) and c.get("claim_id") == claim_id for c in section.get("claims", []))
                    ),
                    None,
                )
                if section_index is not None:
                    target["section_index"] = section_index
                _add_plan(
                    plans,
                    gate="claim_audit",
                    action="revise_claim",
                    target=target,
                    reason=str(item.get("reason", "Claim audit requires revision.")).strip(),
                    evidence_refs=[str(ref) for ref in item.get("evidence_refs", [])] or [str(ref) for ref in claim.get("evidence_refs", [])],
                    rerun_gates=["claim_quality", "claim_audit", "article_draft_quality"],
                )
            if not plans:
                _add_plan(
                    plans,
                    gate="claim_audit",
                    action="revise_claims",
                    target={},
                    reason="Claim Audit requires revision before downstream processing.",
                    rerun_gates=["claim_quality", "claim_audit", "article_draft_quality"],
                )
        else:
            seo = result.get("seo_validation", {})
            if seo.get("outcome") != "passed":
                _add_plan(plans, gate="seo_validation", action="revise_seo", target={}, reason="SEO Validation requires revision.", rerun_gates=["seo_validation", "editorial_review", "publication"])
            else:
                editorial = result.get("editorial_review", {})
                if editorial.get("outcome") != "approved":
                    _add_plan(plans, gate="editorial_review", action="revise_editorial", target={}, reason="Editorial Review did not approve the draft.", rerun_gates=["editorial_review", "publication"])

    outcome = "planned" if plans else "not_required"
    return {
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "revision_plan_ready",
        "outcome": outcome,
        "plans": plans,
        "summary": {
            "total": len(plans),
            "critical": sum(item["priority"] == "critical" for item in plans),
            "targeted": sum(bool(item["target"]) for item in plans),
        },
        "audit": {"method": "autonomous_revision_planner", "version": METHOD_VERSION, "validation_status": "validated"},
    }
