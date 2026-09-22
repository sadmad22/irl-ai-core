from __future__ import annotations

import copy
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
        if (
            "evidence" not in path.stem
            or path.name in {"evidence.json", "editorial-evidence.json"}
        ):
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

    return sorted(
        (
            _normalize_evidence_source(
                _normalize_evidence_provenance(item)
            )
            for item in records
        ),
        key=lambda item: str(item["evidence_id"]),
    )


def _normalize_evidence_provenance(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy Evidence provenance in a runtime-only copy."""
    normalized = copy.deepcopy(record)
    provenance = normalized.get("provenance")
    if not isinstance(provenance, dict):
        return normalized

    has_legacy = "version" in provenance
    has_canonical = "analyzer_version" in provenance

    if has_legacy and has_canonical:
        raise ValueError(
            f"Conflicting Evidence provenance version fields: {record.get('evidence_id', '<unknown>')}"
        )

    if has_legacy:
        provenance["analyzer_version"] = provenance.pop("version")

    return normalized


def _normalize_evidence_source(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy Research-artifact source metadata in a runtime-only copy."""
    normalized = copy.deepcopy(record)
    source = normalized.get("source")
    if not isinstance(source, dict):
        return normalized

    has_legacy = "project" in source or "artifact" in source
    has_canonical = any(
        key in source
        for key in ("source_id", "provider", "retrieved_at")
    )

    if has_legacy and has_canonical:
        raise ValueError(
            f"Conflicting Evidence source fields: {record.get('evidence_id', '<unknown>')}"
        )

    if not has_legacy:
        return normalized

    if source.get("type") != "research_artifact":
        raise ValueError(
            f"Legacy Evidence source type is unsupported: {record.get('evidence_id', '<unknown>')}"
        )

    project = source.get("project")
    artifact = source.get("artifact")
    if (
        not isinstance(project, str)
        or not project.strip()
        or not isinstance(artifact, str)
        or not artifact.strip()
    ):
        raise ValueError(
            f"Legacy Evidence source requires project and artifact: {record.get('evidence_id', '<unknown>')}"
        )

    normalized["source"] = {
        "type": "research_artifact",
        "source_id": f"research/{project}/{artifact}",
        "provider": "local",
        "retrieved_at": None,
    }
    return normalized


def build_intelligence_from_project(project_name: str) -> dict[str, Any]:
    """Build Intelligence from existing Research artifacts without mutating them."""
    research_report = _load(project_name, "research-report.json")
    evidence = _load_evidence_records(project_name)
    return build_intelligence(research_report, evidence)
