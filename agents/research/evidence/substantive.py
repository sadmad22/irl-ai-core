from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from ..expected_claim_map import EXPECTED_CLAIM_MAP
from .domain_common import build_observation

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
SOURCE_MATERIAL_FILE = "source-material.json"
SUBSTANTIVE_EVIDENCE_FILE = "substantive-evidence.json"

_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA = json.loads(
    (_ROOT / "shared" / "schemas" / "substantive-source-material.schema.json").read_text(encoding="utf-8")
)
_VALIDATOR = Draft202012Validator(_SCHEMA, format_checker=FormatChecker())


def _allowed_substantive_claims() -> set[tuple[str, str]]:
    allowed: set[tuple[str, str]] = set()
    for section in EXPECTED_CLAIM_MAP.values():
        for item in (*section["required_claims"], *section["supporting_claims"]):
            if item["evidence_kind"] == "substantive":
                allowed.add((item["claim_type"], item["attribute"]))
    return allowed


_ALLOWED_SUBSTANTIVE_CLAIMS = _allowed_substantive_claims()


def validate_source_material(material: dict[str, Any]) -> None:
    errors = sorted(_VALIDATOR.iter_errors(material), key=lambda error: list(error.path))
    if errors:
        path = ".".join(str(value) for value in errors[0].path) or "<root>"
        raise ValueError(f"Invalid substantive source material at {path}: {errors[0].message}")


def _source_metadata(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": source["type"],
        "source_id": source["source_id"],
        "provider": source["provider"],
        "retrieved_at": source["retrieved_at"],
    }


def _fact_provenance() -> dict[str, str]:
    return {
        "analyzer": "substantive_research",
        "analyzer_version": METHOD_VERSION,
        "method": "source_material_v1",
    }


def _methodology_evidence(
    *,
    report_id: str,
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    metadata = _source_metadata(source)
    subject = {"type": "source", "id": source["source_id"]}
    captured_at = str(source["retrieved_at"])
    provenance = _fact_provenance()
    return [
        build_observation(
            report_id=report_id,
            domain="methodology",
            subject=subject,
            claim={"type": "source_identity", "attribute": "source"},
            value={
                "type": "text",
                "data": f"{source['title']} — {source['url']}",
            },
            source=metadata,
            provenance=provenance,
            confidence=1.0,
            captured_at=captured_at,
        ),
        build_observation(
            report_id=report_id,
            domain="methodology",
            subject=subject,
            claim={"type": "provenance_fact", "attribute": "method"},
            value={
                "type": "text",
                "data": "Source material is converted to canonical Evidence by the deterministic substantive_research_v1 method.",
            },
            source=metadata,
            provenance=provenance,
            confidence=1.0,
            captured_at=captured_at,
        ),
        build_observation(
            report_id=report_id,
            domain="methodology",
            subject=subject,
            claim={"type": "lineage_fact", "attribute": "evidence_lineage"},
            value={
                "type": "text",
                "data": f"{source['source_id']} -> source material -> canonical Evidence",
            },
            source=metadata,
            provenance=provenance,
            confidence=1.0,
            captured_at=captured_at,
        ),
    ]


def build_substantive_evidence(
    *,
    report_id: str,
    material: dict[str, Any],
) -> list[dict[str, Any]]:
    if not str(report_id).strip():
        raise ValueError("report_id is required")
    if not isinstance(material, dict):
        raise TypeError("material must be a dictionary")

    validate_source_material(material)
    if material["project_name"].strip() == "":
        raise ValueError("source material project_name is required")

    records: list[dict[str, Any]] = []
    provenance = _fact_provenance()

    for source in material["sources"]:
        source_metadata = _source_metadata(source)
        captured_at = str(source["retrieved_at"])
        records.extend(_methodology_evidence(report_id=report_id, source=source))
        for fact in source["facts"]:
            pair = (fact["claim_type"], fact["attribute"])
            if pair not in _ALLOWED_SUBSTANTIVE_CLAIMS:
                raise ValueError(
                    f"Substantive research claim is not allowed by Expected Claim Map: "
                    f"{fact['claim_type']}.{fact['attribute']}"
                )
            if fact["claim_type"] in {"query_intent", "entity_presence", "entity_relevance", "question_frequency", "authority"}:
                raise ValueError("Surface/signal claims cannot be emitted by substantive research")

            records.append(
                build_observation(
                    report_id=report_id,
                    domain=f"substantive_{fact['claim_type']}",
                    subject=fact["subject"],
                    claim={"type": fact["claim_type"], "attribute": fact["attribute"]},
                    value=fact["value"],
                    source=source_metadata,
                    provenance=provenance,
                    confidence=fact["confidence"],
                    captured_at=captured_at,
                    evidence_id=None,
                )
            )

    deduped = {record["evidence_id"]: record for record in records}
    return [deduped[key] for key in sorted(deduped)]


def build_substantive_evidence_from_file(
    *,
    report_id: str,
    project_path: str | Path,
) -> list[dict[str, Any]]:
    path = Path(project_path) / SOURCE_MATERIAL_FILE
    if not path.exists():
        return []
    material = json.loads(path.read_text(encoding="utf-8"))
    records = build_substantive_evidence(report_id=report_id, material=material)
    (Path(project_path) / SUBSTANTIVE_EVIDENCE_FILE).write_text(
        json.dumps(records, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return records
