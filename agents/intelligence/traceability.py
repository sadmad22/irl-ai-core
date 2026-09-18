from __future__ import annotations

from typing import Any


_SIGNAL_FIELDS = (
    "intent_interpretation",
    "ambiguity",
    "topic_signals",
    "source_type_signals",
    "commercial_signals",
    "decision_signals",
)


def validate_intelligence_traceability(
    intelligence: dict[str, Any],
    research_report: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> None:
    """Validate that every Intelligence evidence reference traces to Research."""
    if intelligence.get("report_id") != research_report.get("report_id"):
        raise ValueError("Intelligence.report_id must match ResearchReport.report_id")

    report_refs: set[str] = set()
    for refs in research_report.get("evidence_refs", {}).values():
        if isinstance(refs, list):
            report_refs.update(refs)

    if not report_refs:
        raise ValueError("ResearchReport.evidence_refs must not be empty")

    for field in _SIGNAL_FIELDS:
        value = intelligence.get(field)
        signals = [value] if field in ("intent_interpretation", "ambiguity") else value
        if not isinstance(signals, list):
            raise ValueError(f"Intelligence.{field} must contain traceable signals")

        for index, signal in enumerate(signals):
            if not isinstance(signal, dict):
                raise ValueError(f"Intelligence.{field}[{index}] must be an object")
            refs = signal.get("evidence_refs")
            if not isinstance(refs, list) or not refs:
                raise ValueError(f"Intelligence.{field}[{index}] requires evidence_refs")
            if len(refs) != len(set(refs)):
                raise ValueError(f"Intelligence.{field}[{index}] contains duplicate evidence_refs")
            for ref in refs:
                if ref not in report_refs:
                    raise ValueError(
                        f"Intelligence.{field}[{index}] references Evidence outside ResearchReport: {ref}"
                    )
                evidence = evidence_by_id.get(ref)
                if evidence is None:
                    raise ValueError(
                        f"Intelligence.{field}[{index}] references unresolved Evidence: {ref}"
                    )
                if evidence.get("report_id") != research_report.get("report_id"):
                    raise ValueError(
                        f"Intelligence.{field}[{index}] references Evidence with mismatched report_id: {ref}"
                    )
                if evidence.get("status") != "active":
                    raise ValueError(
                        f"Intelligence.{field}[{index}] references non-active Evidence: {ref}"
                    )
