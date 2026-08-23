"""Execution layer for adaptive recovery plans.

The planner decides what should happen; executors perform bounded artifact
mutations. All recovery executors use the same execution contract so new
strategies can be added without expanding the orchestration loop itself.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

EvidenceAcquirer = Callable[[str, str, list[str], Mapping[str, Any]], Any]
ClaimReviser = Callable[[str, str, str, Mapping[str, Any]], Any]


class RecoveryExecutionError(RuntimeError):
    """Raised when a recovery action cannot be executed safely."""


@dataclass(frozen=True)
class RecoveryExecutionContext:
    """Immutable execution envelope shared by every recovery executor."""

    project_name: str
    result: dict[str, Any]
    plan: Mapping[str, Any]


class RecoveryExecutor(Protocol):
    """Contract implemented by every registered recovery executor."""

    strategy: str

    def execute(self, context: RecoveryExecutionContext) -> dict[str, Any]:
        """Execute one bounded recovery action and return an audit record."""
        ...


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


class EvidenceRecoveryExecutor:
    """Executor for the ``acquire_evidence`` recovery strategy."""

    strategy = "acquire_evidence"

    def __init__(self, evidence_acquirer: EvidenceAcquirer):
        self._evidence_acquirer = evidence_acquirer

    def execute(self, context: RecoveryExecutionContext) -> dict[str, Any]:
        return execute_acquire_evidence(
            project_name=context.project_name,
            result=context.result,
            plan=context.plan,
            evidence_acquirer=self._evidence_acquirer,
        )


class ClaimRecoveryExecutor:
    """Executor for the ``revise_claim`` recovery strategy."""

    strategy = "revise_claim"

    def __init__(self, claim_reviser: ClaimReviser):
        self._claim_reviser = claim_reviser

    def execute(self, context: RecoveryExecutionContext) -> dict[str, Any]:
        return execute_revise_claim(
            project_name=context.project_name,
            result=context.result,
            plan=context.plan,
            claim_reviser=self._claim_reviser,
        )


class RecoveryExecutorRegistry:
    """Deterministic registry mapping recovery strategies to executors."""

    def __init__(self, executors: Sequence[RecoveryExecutor] = ()):
        self._executors: dict[str, RecoveryExecutor] = {}
        for executor in executors:
            self.register(executor)

    def register(self, executor: RecoveryExecutor) -> None:
        strategy = str(executor.strategy).strip()
        if not strategy:
            raise ValueError("recovery executor strategy cannot be empty")
        if strategy in self._executors:
            raise ValueError(f"recovery executor already registered: {strategy}")
        self._executors[strategy] = executor

    def get(self, strategy: str) -> RecoveryExecutor:
        try:
            return self._executors[strategy]
        except KeyError as exc:
            raise RecoveryExecutionError(
                f"no executor is registered for recovery strategy: {strategy}"
            ) from exc

    def strategies(self) -> tuple[str, ...]:
        return tuple(sorted(self._executors))


def build_recovery_executor_registry(
    *,
    evidence_acquirer: EvidenceAcquirer | None = None,
    claim_reviser: ClaimReviser | None = None,
) -> RecoveryExecutorRegistry:
    """Build the default registry without registering unsafe placeholders."""
    executors: list[RecoveryExecutor] = []
    if evidence_acquirer is not None:
        executors.append(EvidenceRecoveryExecutor(evidence_acquirer))
    if claim_reviser is not None:
        executors.append(ClaimRecoveryExecutor(claim_reviser))
    return RecoveryExecutorRegistry(executors)


def execute_acquire_evidence(
    *,
    project_name: str,
    result: dict[str, Any],
    plan: Mapping[str, Any],
    evidence_acquirer: EvidenceAcquirer,
) -> dict[str, Any]:
    """Acquire evidence and attach only new references to the targeted claim."""
    if plan.get("strategy") != "acquire_evidence":
        raise RecoveryExecutionError(
            "execute_acquire_evidence received a non-evidence recovery plan"
        )

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
        raise RecoveryExecutionError(
            "evidence acquisition returned no new evidence references"
        )

    claim["evidence_refs"] = existing_refs + new_refs
    return {
        "strategy": "acquire_evidence",
        "status": "executed",
        "target": claim_id,
        "changed": True,
        "previous_evidence_refs": existing_refs,
        "acquired_evidence_refs": new_refs,
        "evidence_refs": claim["evidence_refs"],
    }


def execute_revise_claim(
    *,
    project_name: str,
    result: dict[str, Any],
    plan: Mapping[str, Any],
    claim_reviser: ClaimReviser,
) -> dict[str, Any]:
    """Revise one targeted claim through a bounded claim-reviser callback."""
    if plan.get("strategy") != "revise_claim":
        raise RecoveryExecutionError(
            "execute_revise_claim received a non-claim recovery plan"
        )

    claim_id = str(plan.get("target", "")).strip()
    if not claim_id:
        raise RecoveryExecutionError("revise_claim requires a claim target")

    draft = result.get("article_draft")
    if not isinstance(draft, dict):
        raise RecoveryExecutionError("revise_claim requires an article_draft artifact")

    claim = _find_claim(draft, claim_id)
    if claim is None:
        raise RecoveryExecutionError(f"claim target not found: {claim_id}")

    previous_text = str(claim.get("text", "")).strip()
    if not previous_text:
        raise RecoveryExecutionError("revise_claim requires existing claim text")

    revised = claim_reviser(project_name, claim_id, previous_text, plan)
    if isinstance(revised, Mapping):
        revised_text = str(revised.get("text", "")).strip()
    else:
        revised_text = str(revised).strip()

    if not revised_text:
        raise RecoveryExecutionError("claim revision returned empty text")
    if revised_text == previous_text:
        raise RecoveryExecutionError("claim revision returned unchanged text")

    claim["text"] = revised_text
    return {
        "strategy": "revise_claim",
        "status": "executed",
        "target": claim_id,
        "changed": True,
        "previous_text": previous_text,
        "revised_text": revised_text,
    }


def execute_recovery(
    *,
    project_name: str,
    result: dict[str, Any],
    plan: Mapping[str, Any],
    evidence_acquirer: EvidenceAcquirer | None = None,
    claim_reviser: ClaimReviser | None = None,
    registry: RecoveryExecutorRegistry | None = None,
) -> dict[str, Any]:
    """Execute a recovery plan through the unified executor contract."""
    active_registry = registry or build_recovery_executor_registry(
        evidence_acquirer=evidence_acquirer,
        claim_reviser=claim_reviser,
    )
    strategy = str(plan.get("strategy", "")).strip()
    if not strategy:
        raise RecoveryExecutionError("recovery plan is missing a strategy")
    executor = active_registry.get(strategy)
    return executor.execute(
        RecoveryExecutionContext(
            project_name=project_name,
            result=result,
            plan=plan,
        )
    )
