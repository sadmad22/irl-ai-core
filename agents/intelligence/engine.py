from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from agents.intelligence.input_contract import validate_intelligence_input
from agents.intelligence.traceability import validate_intelligence_traceability


ROOT = Path(__file__).resolve().parents[2]
INTELLIGENCE_SCHEMA_PATH = ROOT / "shared" / "schemas" / "intelligence.schema.json"

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "1.0"

_EVIDENCE_DOMAINS = ("intent", "entity", "question", "business", "authority")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _intelligence_id(report_id: str, context: dict[str, Any]) -> str:
    payload = {
        "report_id": report_id,
        "method_version": METHOD_VERSION,
        "evidence_by_id": context["evidence_by_id"],
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:24]
    return f"int_{digest}"


def _schema_validator() -> Draft202012Validator:
    schema = json.loads(INTELLIGENCE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _refs_for_domain(
    report: dict[str, Any],
    domain: str,
) -> list[str]:
    return list(report["evidence_refs"].get(domain, []))


def _all_refs(report: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for domain in _EVIDENCE_DOMAINS:
        refs.extend(_refs_for_domain(report, domain))
    return refs


def _value_text(evidence: dict[str, Any]) -> str:
    value = evidence.get("value", {})
    data = value.get("data")
    if isinstance(data, (dict, list)):
        return _canonical_json(data)
    return str(data)


def _signal_summary(evidence: dict[str, Any]) -> str:
    claim = evidence["claim"]
    claim_type = claim["type"]
    attribute = claim["attribute"]
    return f"{claim_type}.{attribute}: {_value_text(evidence)}"


def _signals_for_domain(
    evidence_by_id: dict[str, dict[str, Any]],
    refs: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            "summary": _signal_summary(evidence_by_id[ref]),
            "evidence_refs": [ref],
        }
        for ref in refs
    ]


def _source_type_signals(
    evidence_by_id: dict[str, dict[str, Any]],
    refs: list[str],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = {}
    for ref in refs:
        source_type = str(evidence_by_id[ref]["source"]["type"])
        grouped.setdefault(source_type, []).append(ref)

    return [
        {
            "summary": f"Research evidence includes source type: {source_type}.",
            "evidence_refs": grouped[source_type],
        }
        for source_type in sorted(grouped)
    ]


def _ambiguity(
    evidence_by_id: dict[str, dict[str, Any]],
    refs: list[str],
) -> dict[str, Any]:
    contradictory_refs = [
        ref for ref in refs if evidence_by_id[ref]["relation"] == "contradicts"
    ]

    if contradictory_refs:
        return {
            "level": "high",
            "explanation": "Contradictory active evidence is present in the Research input.",
            "evidence_refs": contradictory_refs,
        }

    values_by_claim: dict[tuple[str, str], set[str]] = {}
    refs_by_claim: dict[tuple[str, str], list[str]] = {}
    for ref in refs:
        evidence = evidence_by_id[ref]
        claim = evidence["claim"]
        key = (claim["type"], claim["attribute"])
        values_by_claim.setdefault(key, set()).add(_value_text(evidence))
        refs_by_claim.setdefault(key, []).append(ref)

    conflicting_refs: list[str] = []
    for key in sorted(values_by_claim):
        if len(values_by_claim[key]) > 1:
            conflicting_refs.extend(refs_by_claim[key])

    if conflicting_refs:
        return {
            "level": "medium",
            "explanation": "Multiple values are present for the same evidence claim.",
            "evidence_refs": list(dict.fromkeys(conflicting_refs)),
        }

    return {
        "level": "low",
        "explanation": "No contradiction or conflicting claim values were detected in active Research evidence.",
        "evidence_refs": refs[:1],
    }


def _commercial_signals(
    evidence_by_id: dict[str, dict[str, Any]],
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    refs = _refs_for_domain(report, "business")
    refs = list(dict.fromkeys(refs))
    if not refs:
        return []

    return [
        {
            "summary": "Research contains evidence relevant to commercial considerations.",
            "evidence_refs": refs,
        }
    ]


def _decision_signals(
    evidence_by_id: dict[str, dict[str, Any]],
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    refs = _refs_for_domain(report, "business")
    refs.extend(_refs_for_domain(report, "authority"))
    refs.extend(
        ref
        for ref in _all_refs(report)
        if evidence_by_id[ref]["relation"] == "contradicts"
    )
    refs = list(dict.fromkeys(refs))
    if not refs:
        return []

    return [
        {
            "summary": "Research evidence contains considerations relevant to downstream decision-making.",
            "evidence_refs": refs,
        }
    ]


def _unsupported(
    report: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    messages: list[str] = []
    if not _refs_for_domain(report, "business"):
        messages.append("No business-domain evidence is available in the ResearchReport.")
    if not _refs_for_domain(report, "authority"):
        messages.append("No authority-domain evidence is available in the ResearchReport.")
    if any(
        evidence_by_id[ref]["relation"] == "contradicts"
        for ref in _all_refs(report)
    ):
        messages.append("Contradictory evidence limits confidence in downstream interpretation.")
    return messages


def _derive_intelligence(
    research_report: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    evidence_by_id = context["evidence_by_id"]
    intent_refs = _refs_for_domain(research_report, "intent")
    if not intent_refs:
        raise ValueError("Intelligence requires intent evidence_refs")

    all_refs = _all_refs(research_report)
    primary_intent = research_report["search_intent"].get("primary_intent")
    if primary_intent:
        intent_summary = f"Canonical ResearchReport search intent is {primary_intent}."
    else:
        intent_summary = "ResearchReport search intent is present but does not expose primary_intent."

    result = {
        "intelligence_id": _intelligence_id(research_report["report_id"], context),
        "report_id": research_report["report_id"],
        "intent_interpretation": {
            "summary": intent_summary,
            "evidence_refs": intent_refs,
        },
        "ambiguity": _ambiguity(evidence_by_id, all_refs),
        "topic_signals": _signals_for_domain(
            evidence_by_id,
            _refs_for_domain(research_report, "entity")
            + _refs_for_domain(research_report, "question"),
        ),
        "source_type_signals": _source_type_signals(evidence_by_id, all_refs),
        "commercial_signals": _commercial_signals(evidence_by_id, research_report),
        "decision_signals": _decision_signals(evidence_by_id, research_report),
        "unsupported_or_insufficient": _unsupported(research_report, evidence_by_id),
        "schema_version": SCHEMA_VERSION,
        "method_version": METHOD_VERSION,
        "lifecycle_stage": "intelligence_ready",
    }

    validator = _schema_validator()
    errors = sorted(validator.iter_errors(result), key=lambda error: list(error.path))
    if errors:
        raise ValueError(f"Intelligence artifact is invalid: {errors[0].message}")

    validate_intelligence_traceability(
        result,
        research_report,
        evidence_by_id,
    )
    return result


def build_intelligence(
    research_report: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a deterministic Intelligence artifact after input validation."""
    context = validate_intelligence_input(research_report, evidence)
    return _derive_intelligence(copy.deepcopy(research_report), context)
