from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .agent import run as run_research_agent


ResearchRunner = Callable[[str], None]


def evaluate_research_sufficiency(
    *,
    research_report: dict[str, Any],
    question_analysis: dict[str, Any],
    evidence_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate the minimum conditions required to leave research.

    The loop is intentionally small: a research report, at least one research
    question, and at least one evidence record. It does not score authority,
    learn, draft content, or introduce another executor.
    """
    checks = {
        "research_report": bool(research_report.get("report_id")),
        "research_questions": bool(question_analysis.get("questions")),
        "evidence": bool(evidence_records),
    }
    passed = all(checks.values())
    return {
        "status": "research_complete" if passed else "research_blocked",
        "passed": passed,
        "checks": checks,
        "research_questions": question_analysis.get("questions", []),
        "evidence_count": len(evidence_records),
    }


def _load(project_name: str, filename: str) -> dict[str, Any]:
    path = Path("research") / project_name / filename
    return json.loads(path.read_text(encoding="utf-8"))


def _load_evidence_records(project_name: str) -> list[dict[str, Any]]:
    root = Path("research") / project_name
    records: list[dict[str, Any]] = []
    for path in sorted(root.glob("*-evidence.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, list):
            records.extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            records.append(value)
    return records


def run_minimal_research_loop(
    project_name: str,
    *,
    research_runner: ResearchRunner = run_research_agent,
) -> dict[str, Any]:
    """Run research once, then decide whether the minimum evidence contract is met."""
    research_runner(project_name)
    return evaluate_research_sufficiency(
        research_report=_load(project_name, "research-report.json"),
        question_analysis=_load(project_name, "question-analysis.json"),
        evidence_records=_load_evidence_records(project_name),
    )
