"""Deterministic planning for recovering from research quality-gate failures.

This module deliberately plans recovery only.  It does not mutate artifacts,
acquire evidence, or invoke any of the existing pipeline agents.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal, Mapping, TypedDict

Gate = Literal["claim_audit", "article_draft_quality", "seo_validation", "editorial_review"]
Strategy = Literal[
    "acquire_evidence",
    "revise_claim",
    "revise_section",
    "revise_seo",
    "revise_editorial",
    "stop",
]
RecoveryStatus = Literal["planned", "stopped"]


class RecoveryPlan(TypedDict):
    recovery_id: str
    gate: str
    failure_type: str
    strategy: Strategy
    priority: int
    target: str
    evidence_refs: list[str]
    rationale: str
    actions: list[str]
    rerun_gates: list[str]
    status: RecoveryStatus


_GATE_ORDER = {
    "claim_audit": 0,
    "article_draft_quality": 1,
    "seo_validation": 2,
    "editorial_review": 3,
}
_FAILURE_ORDER = {
    "insufficient_evidence": 0,
    "disputed_claim": 1,
    "missing_evidence_refs": 2,
    "claim_grounding": 3,
    "section_grounding": 4,
    "lineage": 5,
    "seo": 6,
    "editorial": 7,
    "unknown_failure": 99,
}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _refs(value: Any) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return list(dict.fromkeys(ref for ref in (_text(item) for item in value) if ref))


def _recovery_id(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"recovery_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _plan(
    *,
    gate: str,
    failure_type: str,
    strategy: Strategy,
    priority: int,
    target: str,
    evidence_refs: list[str],
    rationale: str,
    actions: list[str],
    rerun_gates: list[str],
    status: RecoveryStatus = "planned",
) -> RecoveryPlan:
    payload: RecoveryPlan = {
        "recovery_id": "",
        "gate": gate,
        "failure_type": failure_type,
        "strategy": strategy,
        "priority": priority,
        "target": target,
        "evidence_refs": list(evidence_refs),
        "rationale": rationale,
        "actions": list(actions),
        "rerun_gates": list(rerun_gates),
        "status": status,
    }
    identity = {key: value for key, value in payload.items() if key != "recovery_id"}
    payload["recovery_id"] = _recovery_id(identity)
    return payload


def _stop(gate: str, failure_type: str, rationale: str, target: str = "") -> RecoveryPlan:
    return _plan(
        gate=gate,
        failure_type=failure_type,
        strategy="stop",
        priority=0,
        target=target,
        evidence_refs=[],
        rationale=rationale,
        actions=["Stop recovery and require explicit human review."],
        rerun_gates=[],
        status="stopped",
    )


def _finding_type(gate: str, finding: Mapping[str, Any]) -> str:
    category = _text(finding.get("category")).lower()
    if gate == "claim_audit":
        if category in {"disputed", "disputed_claim"}:
            return "disputed_claim"
        if category in {"missing_evidence_refs", "evidence_refs"}:
            return "missing_evidence_refs"
        if category in {"insufficient", "insufficient_evidence", "evidence"}:
            return "insufficient_evidence"
    if gate == "article_draft_quality":
        if category in {"section_evidence_grounding", "section_grounding"}:
            return "section_grounding"
        if category in {"claim_evidence_grounding", "claim_grounding"}:
            return "claim_grounding"
        if category == "lineage":
            return "lineage"
    if gate == "seo_validation" and category in {"seo", "seo_revision", "title", "headings", "primary_keyword", "structure"}:
        return "seo"
    if gate == "editorial_review" and category in {"editorial", "editorial_revision", "structure", "evidence", "unsupported_claims"}:
        return "editorial"
    return ""


def _claim_plan(gate: str, failure_type: str, claim: Mapping[str, Any], audit: Mapping[str, Any]) -> RecoveryPlan:
    claim_id = _text(claim.get("claim_id") or audit.get("claim_id"))
    refs = _refs(claim.get("evidence_refs") or audit.get("evidence_refs"))
    if not claim_id:
        return _stop(gate, failure_type, "Recovery requires a claim_id target.")
    if failure_type in {"insufficient_evidence", "missing_evidence_refs", "disputed_claim"}:
        rationale = {
            "disputed_claim": "The claim has contradictory assigned evidence; new or clarifying evidence is required.",
            "missing_evidence_refs": "The claim has no usable evidence references.",
            "insufficient_evidence": "The assigned evidence does not sufficiently support the claim.",
        }[failure_type]
        return _plan(
            gate=gate,
            failure_type=failure_type,
            strategy="acquire_evidence",
            priority=1,
            target=claim_id,
            evidence_refs=refs,
            rationale=rationale,
            actions=["Acquire authoritative evidence for the claim.", "Attach verified evidence references to the claim."],
            rerun_gates=["claim_audit"],
        )
    return _plan(
        gate=gate,
        failure_type=failure_type,
        strategy="revise_claim",
        priority=2,
        target=claim_id,
        evidence_refs=refs,
        rationale="The claim does not satisfy claim-level grounding requirements.",
        actions=["Revise or remove the targeted claim.", "Preserve evidence lineage while revising the claim."],
        rerun_gates=["article_draft_quality", "claim_audit"],
    )


def _plans_for_gate(gate: str, result: Mapping[str, Any]) -> list[RecoveryPlan]:
    if gate not in _GATE_ORDER:
        return [_stop(gate, "unknown_gate", "The recovery planner does not recognize this gate.")]
    outcome = _text(result.get("outcome")).lower()
    healthy = outcome in {"passed", "approved", "allowed", "supported"}
    if healthy:
        return []

    plans: list[RecoveryPlan] = []
    if gate == "claim_audit":
        for audit in result.get("claims", []) if isinstance(result.get("claims"), list) else []:
            if not isinstance(audit, Mapping):
                plans.append(_stop(gate, "unknown_failure", "Claim audit failure data is not structured."))
                continue
            result_type = _text(audit.get("result")).lower()
            failure_type = {
                "insufficient": "insufficient_evidence",
                "disputed": "disputed_claim",
            }.get(result_type)
            if result_type == "insufficient" and not _refs(audit.get("evidence_refs")):
                failure_type = "missing_evidence_refs"
            if not failure_type:
                plans.append(_stop(gate, "unknown_failure", "Claim audit returned an unsupported failure type."))
                continue
            plans.append(_claim_plan(gate, failure_type, audit, audit))
        if not plans:
            plans.append(_stop(gate, "unknown_failure", "Claim audit did not identify a recoverable claim failure."))
        return plans

    findings = result.get("findings", [])
    if not isinstance(findings, list) or not findings:
        return [_stop(gate, "unknown_failure", "The failed gate did not provide structured findings.")]
    for finding in findings:
        if not isinstance(finding, Mapping):
            plans.append(_stop(gate, "unknown_failure", "Gate finding is not structured."))
            continue
        failure_type = _finding_type(gate, finding)
        if not failure_type:
            plans.append(_stop(gate, "unknown_failure", "The gate returned an unsupported failure category."))
            continue
        if gate == "article_draft_quality":
            target = _text(finding.get("target") or result.get("draft_id"))
            if failure_type == "claim_grounding":
                claim = finding.get("claim") if isinstance(finding.get("claim"), Mapping) else finding
                plans.append(_claim_plan(gate, failure_type, claim, finding))
            elif failure_type == "section_grounding":
                if not target:
                    plans.append(_stop(gate, failure_type, "Section grounding recovery requires a section target."))
                else:
                    plans.append(_plan(gate=gate, failure_type=failure_type, strategy="revise_section", priority=2, target=target, evidence_refs=_refs(finding.get("evidence_refs")), rationale="The targeted section is not sufficiently grounded.", actions=["Revise the targeted section using verified evidence.", "Preserve section and evidence lineage."], rerun_gates=["article_draft_quality", "claim_audit"]))
            else:
                plans.append(_stop(gate, failure_type, "Lineage failures cannot be repaired safely without explicit artifact review.", target))
        elif gate == "seo_validation":
            target = _text(finding.get("target") or result.get("draft_id"))
            if not target:
                plans.append(_stop(gate, failure_type, "SEO recovery requires a draft target."))
            else:
                plans.append(_plan(gate=gate, failure_type=failure_type, strategy="revise_seo", priority=2, target=target, evidence_refs=_refs(result.get("evidence_refs")), rationale="The draft does not satisfy the SEO validation requirements.", actions=["Apply a targeted SEO revision to the draft.", "Preserve keyword, heading, and evidence lineage."], rerun_gates=["seo_validation"]))
        else:
            target = _text(finding.get("target") or result.get("draft_id"))
            if not target:
                plans.append(_stop(gate, failure_type, "Editorial recovery requires a draft target."))
            else:
                plans.append(_plan(gate=gate, failure_type=failure_type, strategy="revise_editorial", priority=2, target=target, evidence_refs=_refs(result.get("evidence_refs")), rationale="The draft does not satisfy editorial review requirements.", actions=["Apply a targeted editorial revision to the draft.", "Preserve evidence and artifact lineage."], rerun_gates=["editorial_review"]))
    return plans


def plan_recovery(*, gate: str, result: Mapping[str, Any]) -> RecoveryPlan | None:
    """Return one plan for a single failure, or ``None`` for a healthy result."""
    plans = _plans_for_gate(gate, result)
    return plans[0] if plans else None


def plan_recoveries(*, results: Mapping[str, Mapping[str, Any]]) -> list[RecoveryPlan]:
    """Plan all failed gates in stable gate/failure order."""
    plans = [
        plan
        for gate in sorted(results, key=lambda name: (_GATE_ORDER.get(name, 99), name))
        for plan in _plans_for_gate(gate, results[gate])
    ]
    return sorted(plans, key=lambda plan: (_GATE_ORDER.get(plan["gate"], 99), plan["target"], _FAILURE_ORDER.get(plan["failure_type"], 99), plan["recovery_id"]))


build_recovery_plan = plan_recovery
build_recovery_plans = plan_recoveries
