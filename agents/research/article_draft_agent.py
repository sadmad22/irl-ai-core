from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .content_brief_agent import run as run_content_brief_agent
from .article_draft import build_article_draft


def _load(project: str, filename: str) -> dict[str, Any]:
    path = Path("research") / project / filename
    return json.loads(path.read_text(encoding="utf-8"))


def _load_evidence_records(project: str) -> list[dict[str, Any]]:
    root = Path("research") / project
    records: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        if "evidence" not in path.stem:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, list):
            records.extend(item for item in data if isinstance(item, dict) and item.get("evidence_id"))
        elif isinstance(data, dict) and data.get("evidence_id"):
            records.append(data)
    return sorted(records, key=lambda item: str(item["evidence_id"]))


def _save_if_changed(project: str, filename: str, data: dict[str, Any]) -> None:
    path = Path("research") / project / filename
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if current != data:
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


def run(project_name: str) -> dict[str, Any]:
    """Run Content Brief then materialize an evidence-grounded Article Draft."""
    run_content_brief_agent(project_name)

    brief = _load(project_name, "content-brief.json")
    evidence_records = _load_evidence_records(project_name)
    draft = build_article_draft(
        content_brief=brief,
        evidence_records=evidence_records,
    )
    _save_if_changed(project_name, "article-draft.json", draft)

    metadata_path = Path("research") / project_name / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["project_name"] = project_name
    metadata["status"] = "draft_ready"
    metadata_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")

    return draft
