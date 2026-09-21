from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .editorial_source_evidence import build_editorial_evidence


def _load_json(project: str, filename: str) -> Any:
    path = Path("research") / project / filename
    return json.loads(path.read_text(encoding="utf-8"))


def _load_research_evidence(project: str) -> list[dict[str, Any]]:
    root = Path("research") / project
    records: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        if "evidence" not in path.stem or path.stem == "editorial-evidence":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, list):
            records.extend(
                item for item in data
                if isinstance(item, dict) and item.get("evidence_id")
            )
        elif isinstance(data, dict) and data.get("evidence_id"):
            records.append(data)
    return sorted(records, key=lambda item: str(item["evidence_id"]))


def _normalize_source_pages(data: Any) -> dict[str, dict[str, Any]]:
    if isinstance(data, dict):
        pages: dict[str, dict[str, Any]] = {}
        for key, value in data.items():
            evidence_id = str(key).strip()
            if not evidence_id:
                raise ValueError(
                    "editorial-source-pages.json requires non-empty evidence_id keys"
                )
            if not isinstance(value, dict):
                raise ValueError(
                    "editorial-source-pages.json must map evidence_id to source-page objects"
                )
            pages[evidence_id] = value
        return pages

    if isinstance(data, list):
        pages: dict[str, dict[str, Any]] = {}
        for item in data:
            if not isinstance(item, dict):
                raise ValueError("editorial-source-pages.json entries must be objects")
            evidence_id = str(item.get("evidence_id", "")).strip()
            if not evidence_id:
                raise ValueError("Editorial source page requires evidence_id")
            if evidence_id in pages:
                raise ValueError(
                    f"Editorial source page contains duplicate evidence_id: {evidence_id}"
                )
            page = {key: value for key, value in item.items() if key != "evidence_id"}
            pages[evidence_id] = page
        return pages

    raise ValueError("editorial-source-pages.json must contain an object or array")


def _save_if_changed(project: str, filename: str, data: list[dict[str, Any]]) -> None:
    path = Path("research") / project / filename
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if current != data:
        path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )


def run(project_name: str) -> list[dict[str, Any]]:
    """Materialize Editorial Source Evidence from an explicit source-page artifact.

    Source-page retrieval is intentionally outside this function. This agent only
    projects verified upstream page material onto canonical Research Evidence IDs.
    If no source-page artifact exists, the optional boundary remains inactive.
    """
    source_path = Path("research") / project_name / "editorial-source-pages.json"
    if not source_path.exists():
        return []

    source_pages = _normalize_source_pages(
        _load_json(project_name, "editorial-source-pages.json")
    )
    evidence_records = _load_research_evidence(project_name)
    editorial_evidence = build_editorial_evidence(
        evidence_records=evidence_records,
        source_pages=source_pages,
    )
    _save_if_changed(project_name, "editorial-evidence.json", editorial_evidence)
    return editorial_evidence
