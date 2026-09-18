from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.intelligence.engine import build_intelligence


def _load(project_name: str, filename: str) -> dict[str, Any]:
    path = Path("research") / project_name / filename
    if not path.exists():
        raise ValueError(f"Required Research artifact is missing: {filename}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_evidence_records(project_name: str) -> list[dict[str, Any]]:
    root = Path("research") / project_name
    if not root.exists():
        raise ValueError(f"Research project is missing: {project_name}")

    records: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        if "evidence" not in path.stem:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid Research Evidence artifact: {path.name}") from exc

        if isinstance(data, list):
            records.extend(
                item
                for item in data
                if isinstance(item, dict) and item.get("evidence_id")
            )
        elif isinstance(data, dict) and data.get("evidence_id"):
            records.append(data)

    return sorted(records, key=lambda item: str(item["evidence_id"]))


def build_intelligence_from_project(project_name: str) -> dict[str, Any]:
    """Build Intelligence from existing Research artifacts without mutating them."""
    research_report = _load(project_name, "research-report.json")
    evidence = _load_evidence_records(project_name)
    return build_intelligence(research_report, evidence)
