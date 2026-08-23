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
SectionReviser = Callable[[str, str, str, Mapping[str, Any]], Any]
SeoReviser = Callable[[str, str, Mapping[str, Any], Mapping[str, Any]], Any]


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


def _find_section(article_draft: Mapping[str, Any], target: str) -> dict[str, Any] | None:
    normalized = target.strip().casefold()
    for section in article_draft.get("sections", []):
        if not isinstance(section, dict):
            continue
        candidates = (
            section.get("section_id"),
            section.get("id"),
            section.get("title"),
            section.get("heading"),
        )
        if any(str(candidate or "").strip().casefold() == normalized for candidate in candidates):
            return section
    return None


class EvidenceRecoveryExecutor:
    """Executor for the ``acquire_evidence`` recovery strategy."""

    strategy = "acquire_evidence"

    def __init__(self, evidence_acquirer: EvidenceAcquirer):
        self._evidence_acquirer = evidence_acquirer

    def execute(self, context: RecoveryExecutionContext) -> dict[str, Any]:
        return execute_acquire_evidence(project_name=context.project_name, result=context.result, plan=context.plan, evidence_acquirer=self._evidence_acquirer)


class ClaimRecoveryExecutor:
    """Executor for the ``revise_claim`` recovery strategy."""

    strategy = "revise_claim"

    def __init__(self, claim_reviser: ClaimReviser):
        self._claim_reviser = claim_reviser

    def execute(self, context: RecoveryExecutionContext) -> dict[str, Any]:
        return execute_revise_claim(project_name=context.project_name, result=context.result, plan=context.plan, claim_reviser=self._claim_reviser)


class SectionRecoveryExecutor:
    """Executor for the ``revise_section`` recovery strategy."""

    strategy = "revise_section"

    def __init__(self, section_reviser: SectionReviser):
        self._section_reviser = section_reviser

    def execute(self, context: RecoveryExecutionContext) -> dict[str, Any]:
        return execute_revise_section(project_name=context.project_name, result=context.result, plan=context.plan, section_reviser=self._section_reviser)


class SeoRecoveryExecutor:
    """Executor for the ``revise_seo`` recovery strategy."""

    strategy = "revise_seo"

    def __init__(self, seo_reviser: SeoReviser):
        self._seo_reviser = seo_reviser

    def execute(self, context: RecoveryExecutionContext) -> dict[str, Any]:
        return execute_revise_seo(project_name=context.project_name, result=context.result, plan=context.plan, seo_reviser=self._seo_reviser)


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
            raise RecoveryExecutionError(f"no executor is registered for recovery strategy: {strategy}") from exc

    def strategies(self) -> tuple[str, ...]:
        return tuple(sorted(self._executors))


def build_recovery_executor_registry(
    *, evidence_acquirer: EvidenceAcquirer | None = None,
    claim_reviser: ClaimReviser | None = None,
    section_reviser: SectionReviser | None = None,
    seo_reviser: SeoReviser | None = None,
) -> RecoveryExecutorRegistry:
    """Build the default registry without registering unsafe placeholders."""
    executors: list[RecoveryExecutor] = []
    if evidence_acquirer is not None:
        executors.append(EvidenceRecoveryExecutor(evidence_acquirer))
    if claim_reviser is not None:
        executors.append(ClaimRecoveryExecutor(claim_reviser))
    if section_reviser is not None:
        executors.append(SectionRecoveryExecutor(section_reviser))
    if seo_reviser is not None:
        executors.append(SeoRecoveryExecutor(seo_reviser))
    return RecoveryExecutorRegistry(executors)


def execute_acquire_evidence(*, project_name: str, result: dict[str, Any], plan: Mapping[str, Any], evidence_acquirer: EvidenceAcquirer) -> dict[str, Any]:
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
    return {"strategy": "acquire_evidence", "status": "executed", "target": claim_id, "changed": True, "previous_evidence_refs": existing_refs, "acquired_evidence_refs": new_refs, "evidence_refs": claim["evidence_refs"]}


def execute_revise_claim(*, project_name: str, result: dict[str, Any], plan: Mapping[str, Any], claim_reviser: ClaimReviser) -> dict[str, Any]:
    if plan.get("strategy") != "revise_claim":
        raise RecoveryExecutionError("execute_revise_claim received a non-claim recovery plan")
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
    revised_text = str(revised.get("text", "")).strip() if isinstance(revised, Mapping) else str(revised).strip()
    if not revised_text:
        raise RecoveryExecutionError("claim revision returned empty text")
    if revised_text == previous_text:
        raise RecoveryExecutionError("claim revision returned unchanged text")
    claim["text"] = revised_text
    return {"strategy": "revise_claim", "status": "executed", "target": claim_id, "changed": True, "previous_text": previous_text, "revised_text": revised_text}


def execute_revise_section(*, project_name: str, result: dict[str, Any], plan: Mapping[str, Any], section_reviser: SectionReviser) -> dict[str, Any]:
    """Revise exactly one targeted section while preserving its metadata."""
    if plan.get("strategy") != "revise_section":
        raise RecoveryExecutionError("execute_revise_section received a non-section recovery plan")
    target = str(plan.get("target", "")).strip()
    if not target:
        raise RecoveryExecutionError("revise_section requires a section target")
    draft = result.get("article_draft")
    if not isinstance(draft, dict):
        raise RecoveryExecutionError("revise_section requires an article_draft artifact")
    section = _find_section(draft, target)
    if section is None:
        raise RecoveryExecutionError(f"section target not found: {target}")
    field = next((name for name in ("content", "text", "body") if name in section), None)
    previous_text = str(section.get(field, "")).strip() if field else ""
    if not previous_text:
        raise RecoveryExecutionError("revise_section requires existing section content")
    revised = section_reviser(project_name, target, previous_text, plan)
    revised_text = str(revised.get("content", revised.get("text", revised.get("body", "")))).strip() if isinstance(revised, Mapping) else str(revised).strip()
    if not revised_text:
        raise RecoveryExecutionError("section revision returned empty content")
    if revised_text == previous_text:
        raise RecoveryExecutionError("section revision returned unchanged content")
    section[field or "content"] = revised_text
    return {"strategy": "revise_section", "status": "executed", "target": target, "changed": True, "field": field or "content", "previous_text": previous_text, "revised_text": revised_text}


def execute_revise_seo(*, project_name: str, result: dict[str, Any], plan: Mapping[str, Any], seo_reviser: SeoReviser) -> dict[str, Any]:
    """Apply a bounded SEO metadata mutation to the targeted article draft."""
    if plan.get("strategy") != "revise_seo":
        raise RecoveryExecutionError("execute_revise_seo received a non-SEO recovery plan")
    target = str(plan.get("target", "")).strip()
    if not target:
        raise RecoveryExecutionError("revise_seo requires a draft target")
    draft = result.get("article_draft")
    if not isinstance(draft, dict):
        raise RecoveryExecutionError("revise_seo requires an article_draft artifact")
    draft_id = str(draft.get("draft_id", "")).strip()
    if draft_id and draft_id != target:
        raise RecoveryExecutionError(f"SEO target does not match article_draft: {target}")
    allowed = {"title", "meta_description", "primary_keyword", "slug"}
    previous = {key: draft[key] for key in allowed if key in draft}
    if not previous:
        raise RecoveryExecutionError("revise_seo requires SEO metadata on the article_draft")
    revised = seo_reviser(project_name, target, dict(previous), plan)
    if not isinstance(revised, Mapping):
        raise RecoveryExecutionError("SEO revision must return a mapping of SEO fields")
    unknown = set(revised) - allowed
    if unknown:
        raise RecoveryExecutionError(f"SEO revision returned unsupported fields: {sorted(unknown)}")
    changes = {key: str(value).strip() for key, value in revised.items() if key in allowed}
    if not changes:
        raise RecoveryExecutionError("SEO revision returned no changes")
    changed: dict[str, str] = {}
    for key, value in changes.items():
        if not value:
            raise RecoveryExecutionError(f"SEO revision returned empty value for: {key}")
        if str(previous.get(key, "")).strip() == value:
            continue
        draft[key] = value
        changed[key] = value
    if not changed:
        raise RecoveryExecutionError("SEO revision returned unchanged metadata")
    return {"strategy": "revise_seo", "status": "executed", "target": target, "changed": True, "previous": previous, "revised": changed}


def execute_recovery(*, project_name: str, result: dict[str, Any], plan: Mapping[str, Any], evidence_acquirer: EvidenceAcquirer | None = None, claim_reviser: ClaimReviser | None = None, section_reviser: SectionReviser | None = None, seo_reviser: SeoReviser | None = None, registry: RecoveryExecutorRegistry | None = None) -> dict[str, Any]:
    """Execute a recovery plan through the unified executor contract."""
    active_registry = registry or build_recovery_executor_registry(evidence_acquirer=evidence_acquirer, claim_reviser=claim_reviser, section_reviser=section_reviser, seo_reviser=seo_reviser)
    strategy = str(plan.get("strategy", "")).strip()
    if not strategy:
        raise RecoveryExecutionError("recovery plan is missing a strategy")
    executor = active_registry.get(strategy)
    return executor.execute(RecoveryExecutionContext(project_name=project_name, result=result, plan=plan))