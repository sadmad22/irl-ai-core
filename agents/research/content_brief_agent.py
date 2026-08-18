from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent import run as run_research_agent
from .content_brief_runner import run_content_brief_from_artifacts


def _load(project: str, filename: str) -> dict[str, Any]:
    path = Path("research") / project / filename
    return json.loads(path.read_text(encoding="utf-8"))


def _save_if_changed(project: str, filename: str, data: dict[str, Any]) -> None:
    path = Path("research") / project / filename
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if current != data:
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


def run(project_name: str) -> dict[str, Any]:
    """Run the existing research/decision pipeline, then materialize its Content Brief.

    This wrapper deliberately keeps Content Brief downstream of the existing
    Research Agent. It does not create a new decision or rewrite upstream
    artifacts.
    """
    run_research_agent(project_name)

    report = _load(project_name, "research-report.json")
    decision = _load(project_name, "decision.json")
    strategy = _load(project_name, "content-strategy.json")

    brief = run_content_brief_from_artifacts(
        research_report=report,
        decision=decision,
        content_strategy=strategy,
    )
    _save_if_changed(project_name, "content-brief.json", brief)

    metadata_path = Path("research") / project_name / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["project_name"] = project_name
    metadata["status"] = "content_brief_ready"
    metadata_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")

    return brief
