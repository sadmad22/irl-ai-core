"""Execution layer for adaptive recovery plans.

The planner decides what should happen; executors perform the bounded artifact
mutation.  This module currently implements the first real recovery action:
``acquire_evidence``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

EvidenceAcquirer = Callable[[str, str, list[str], Mapping[str, Any]], Any]


class RecoveryExecutionError(RuntimeError):
    """Raised when a recovery action cannot be executed safely."""


def _normalise_refs(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        value = value.get("evidence_refs")
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return []
    return list(dict.fromkeys(str(ref).strip() for ref in value if str(ref).strip()))


def _find_claim(article_draft: Mapping[str, Any], claim_id: str) -> dict[str, Any] | None:
    for section in article_draft.get("sections", []):
        if not isinstance(section, Mapping):
            continue
        for claim in section.get("claims", []):
            if isinstance(claim, dict) and str(claim.get("claim_id", "")).strip() == claim_id:
                return claim
    return None


def execute_acquire_evidence(
    *,
    project_name: str,
    result: dict[str, Any],
    plan: Mapping[str, Any],
    evidence_acquirer: EvidenceAcquirer,
) -> dict[str, Any]:
    """Acquire authoritative evidence and attach it to the targeted claim.

    The acquirer is the domain-specific research boundary.  It must return one
    or more evidence references (or ``{"evidence_refs": [...]}``).  The
    executor then mutates only the targeted claim and returns an auditable
    execution record.  Empty acquisition results fail closed.
    """
    if plan.get("strategy") != "acquire_evidence":
        raise RecoveryExecutionError("execute_acquire_evidence received a non-evidence recovery plan")

    claim_id = str(plan.get("target", "")).strip()
    if not claim_id:
        raise RecoveryExecutionError("acquire_evidence requires a claim target")

    draft = result.get("article_draft")
    if not isinstance(draft, dict):
        raise RecoveryExecutionError("acquire_evidence requires an article_draft artifact")

    claim = _find_claim(draft, claim_id)
    if claim is None:
        raise RecoveryExecutionError(f"claim target not found: {claim_id}")

    existing_refs = _normalise_refs(claim.get("evidence_refs"))
    acquired = _normalise_refs(evidence_acquirer(project_name, claim_id, existing_refs, plan))
    new_refs = [ref for ref in acquired if ref not in existing_refs]
    if not new_refs:
        raise RecoveryExecutionError("evidence acquisition returned no new evidence references")

    claim["evidence_refs"] = existing_refs + new_refs
    return {
        "strategy": "acquire_evidence",
        "status": "executed",
        "target": claim_id,
        "previous_evidence_refs": existing_refs,
        "acquired_evidence_refs": new_refs,
        "evidence_refs": claim["evidence_refs"],
    }


def execute_recovery(
    *,
    project_name: str,
    result: dict[str, Any],
    plan: Mapping[str, Any],
    evidence_acquirer: EvidenceAcquirer | None = None,
) -> dict[str, Any]:
    """Execute the supported recovery strategy, failing closed otherwise."""
    strategy = plan.get("strategy")
    if strategy == "acquire_evidence":
        if evidence_acquirer is None:
            raise RecoveryExecutionError("no evidence_acquirer configured for acquire_evidence")
        return execute_acquire_evidence(
            project_name=project_name,
            result=result,
            plan=plan,
            evidence_acquirer=evidence_acquirer,
        )
    raise RecoveryExecutionError(f"no executor is registered for recovery strategy: {strategy}")
