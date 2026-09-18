from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_SCHEMA_PATH = ROOT / "shared" / "schemas" / "evidence.schema.json"

_ALLOWED_EVIDENCE_STATUSES = {"active"}
_REQUIRED_REPORT_FIELDS = ("report_id", "search_intent", "evidence_refs")
_REQUIRED_EVIDENCE_REFS_DOMAINS = ("intent", "entity", "question", "business", "authority")


def _evidence_validator() -> Draft202012Validator:
    schema = json.loads(EVIDENCE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _require_report_shape(research_report: Any) -> dict[str, Any]:
    if not isinstance(research_report, dict):
        raise ValueError("ResearchReport must be a dictionary")

    for field in _REQUIRED_REPORT_FIELDS:
        if field not in research_report:
            raise ValueError(f"ResearchReport.{field} is required")

    report_id = research_report.get("report_id")
    if not isinstance(report_id, str) or not report_id.strip():
        raise ValueError("ResearchReport.report_id is required")

    if not isinstance(research_report.get("search_intent"), dict):
        raise ValueError("ResearchReport.search_intent is required")

    evidence_refs = research_report.get("evidence_refs")
    if not isinstance(evidence_refs, dict):
        raise ValueError("ResearchReport.evidence_refs is required")

    for domain in _REQUIRED_EVIDENCE_REFS_DOMAINS:
        refs = evidence_refs.get(domain)
        if refs is None:
            raise ValueError(f"ResearchReport.evidence_refs.{domain} is required")
        if not isinstance(refs, list):
            raise ValueError(f"ResearchReport.evidence_refs.{domain} must be a list")
        if len(refs) != len(set(refs)):
            raise ValueError(f"ResearchReport.evidence_refs.{domain} contains duplicate evidence_refs")
        if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise ValueError(f"ResearchReport.evidence_refs.{domain} contains an invalid evidence_ref")

    return research_report


def _validate_evidence_item(
    validator: Draft202012Validator,
    item: Any,
    *,
    index: int,
    report_id: str,
) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"Evidence[{index}] must be a dictionary")

    errors = sorted(validator.iter_errors(item), key=lambda error: list(error.path))
    if errors:
        raise ValueError(f"Evidence[{index}] is invalid: {errors[0].message}")

    evidence_id = item["evidence_id"]
    if item["report_id"] != report_id:
        raise ValueError(
            f"Evidence[{index}].report_id must match ResearchReport.report_id"
        )

    if item["status"] not in _ALLOWED_EVIDENCE_STATUSES:
        raise ValueError(
            f"Evidence[{index}].status must be active before Intelligence derivation"
        )

    return item


def validate_intelligence_input(
    research_report: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate the complete ResearchReport/Evidence boundary before derivation.

    This function performs no signal derivation and returns only runtime
    validation context for the Intelligence Engine.
    """
    report = _require_report_shape(research_report)

    if not isinstance(evidence, list):
        raise ValueError("evidence must be a list")

    report_id = report["report_id"]
    validator = _evidence_validator()
    evidence_by_id: dict[str, dict[str, Any]] = {}

    for index, item in enumerate(evidence):
        validated = _validate_evidence_item(
            validator,
            item,
            index=index,
            report_id=report_id,
        )
        evidence_id = validated["evidence_id"]
        if evidence_id in evidence_by_id:
            raise ValueError(f"duplicate evidence_id: {evidence_id}")
        evidence_by_id[evidence_id] = validated

    all_refs: list[str] = []
    for domain in _REQUIRED_EVIDENCE_REFS_DOMAINS:
        all_refs.extend(report["evidence_refs"][domain])

    if not all_refs:
        raise ValueError("ResearchReport.evidence_refs must not be empty")

    if len(all_refs) != len(set(all_refs)):
        raise ValueError("duplicate evidence_refs")

    missing = [ref for ref in all_refs if ref not in evidence_by_id]
    if missing:
        raise ValueError(f"evidence_refs contains unresolved references: {missing}")

    return {
        "report_id": report_id,
        "evidence_by_id": copy.deepcopy(evidence_by_id),
    }
