from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .domain_common import build_observation

PIPELINE_METHODOLOGY_EVIDENCE_FILE = "pipeline-methodology-evidence.json"
METHOD_VERSION = "v1"
METHOD = "pipeline_metadata_v1"

_PIPELINE_CLAIMS = (
    ("source_identity", "source", "source-documents.json"),
    ("source_identity", "provider", "source-documents.json"),
    ("provenance_fact", "method", "passage-bound-source-material.json"),
    ("provenance_fact", "analyzer", "passage-bound-source-material.json"),
    ("provenance_fact", "analyzer_version", "passage-bound-source-material.json"),
    ("lineage_fact", "evidence_lineage", "passage-bound-evidence-lineage.json"),
    ("evidence_status", "status", "substantive-evidence.json"),
)

_ROOT = Path(__file__).resolve().parents[3]
_EVIDENCE_VALIDATOR = Draft202012Validator(
    json.loads((_ROOT / "shared" / "schemas" / "evidence.schema.json").read_text(encoding="utf-8"))
)


def _load(project_root: Path, filename: str) -> Any:
    path = project_root / filename
    if not path.is_file():
        raise FileNotFoundError(f"{filename} is required for pipeline methodology evidence")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{filename} is unreadable or invalid JSON") from exc


def _latest_timestamp(documents: list[dict[str, Any]]) -> str:
    values: list[datetime] = []
    for document in documents:
        value = str(document.get("retrieved_at", "")).strip()
        if not value:
            raise ValueError("source document is missing retrieved_at")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("source document retrieved_at is invalid") from exc
        if parsed.tzinfo is None:
            raise ValueError("source document retrieved_at must include a timezone")
        values.append(parsed.astimezone(timezone.utc))
    if not values:
        raise ValueError("source documents must not be empty")
    return max(values).isoformat()


def _save_if_changed(project_root: Path, records: list[dict[str, Any]]) -> None:
    path = project_root / PIPELINE_METHODOLOGY_EVIDENCE_FILE
    current = None
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = None
    if current != records:
        path.write_text(json.dumps(records, indent=4, ensure_ascii=False), encoding="utf-8")


def build_pipeline_methodology_evidence(
    *,
    report_id: str,
    project_path: str | Path,
) -> list[dict[str, Any]]:
    """Build internal provenance Evidence from accepted pipeline artifacts, not insurer-page claims."""
    if not str(report_id).strip():
        raise ValueError("report_id is required")

    root = Path(project_path)
    material = _load(root, "passage-bound-source-material.json")
    documents = _load(root, "source-documents.json")
    passages = _load(root, "extracted-passages.json")
    lineage = _load(root, "passage-bound-evidence-lineage.json")
    substantive = _load(root, "substantive-evidence.json")

    if not all(isinstance(item, dict) for item in (material, documents, passages, lineage)):
        raise ValueError("pipeline methodology inputs must be JSON objects")
    if not isinstance(substantive, list):
        raise ValueError("substantive-evidence.json must contain an array")

    project_name = str(material.get("project_name", "")).strip()
    if not project_name:
        raise ValueError("passage-bound source material project_name is required")

    for label, payload in (
        ("source-documents.json", documents),
        ("extracted-passages.json", passages),
        ("passage-bound-evidence-lineage.json", lineage),
    ):
        if payload.get("project_name") != project_name:
            raise ValueError(f"{label} project_name does not match passage-bound source material")

    for field in ("request_fingerprint", "acquisition_policy_version", "extraction_policy_version"):
        expected = material.get(field)
        if documents.get(field) != expected or passages.get(field) != expected:
            raise ValueError(f"pipeline methodology corpus identity mismatch: {field}")
    if lineage.get("request_fingerprint") != material.get("request_fingerprint"):
        raise ValueError("pipeline methodology lineage request_fingerprint mismatch")

    document_list = documents.get("documents")
    passage_list = passages.get("passages")
    bindings = lineage.get("bindings")
    lineage_ids = lineage.get("evidence_ids")
    if not isinstance(document_list, list) or not document_list:
        raise ValueError("source-documents.json must contain documents")
    if not isinstance(passage_list, list) or not passage_list:
        raise ValueError("extracted-passages.json must contain passages")
    if not isinstance(bindings, list) or not bindings or not isinstance(lineage_ids, list):
        raise ValueError("passage-bound evidence lineage must contain bindings and evidence_ids")

    canonical_ids = [
        str(record.get("evidence_id", "")).strip()
        for record in substantive
        if isinstance(record, dict) and str(record.get("evidence_id", "")).strip()
    ]
    binding_ids = [
        str(binding.get("evidence_id", "")).strip()
        for binding in bindings
        if isinstance(binding, dict) and str(binding.get("evidence_id", "")).strip()
    ]
    if (
        not canonical_ids
        or len(canonical_ids) != len(substantive)
        or len(canonical_ids) != len(set(canonical_ids))
        or set(canonical_ids) != set(lineage_ids)
        or set(canonical_ids) != set(binding_ids)
    ):
        raise ValueError("pipeline methodology requires exact canonical Evidence-to-lineage identity")

    documents_by_id = {
        str(item.get("source_document_id", "")).strip(): item
        for item in document_list
        if isinstance(item, dict) and str(item.get("source_document_id", "")).strip()
    }
    passages_by_id = {
        str(item.get("passage_id", "")).strip(): item
        for item in passage_list
        if isinstance(item, dict) and str(item.get("passage_id", "")).strip()
    }
    if len(documents_by_id) != len(document_list) or len(passages_by_id) != len(passage_list):
        raise ValueError("source document or passage identifiers are missing or duplicated")

    for binding in bindings:
        if not isinstance(binding, dict):
            raise ValueError("pipeline methodology lineage binding must be an object")
        document_id = str(binding.get("source_document_id", "")).strip()
        document = documents_by_id.get(document_id)
        if document is None or document.get("source_id") != binding.get("source_id"):
            raise ValueError("pipeline methodology lineage references an unknown source document")
        passage_ids = binding.get("passage_ids")
        if not isinstance(passage_ids, list) or not passage_ids:
            raise ValueError("pipeline methodology lineage binding has no passage_ids")
        for passage_id in passage_ids:
            passage = passages_by_id.get(str(passage_id))
            if passage is None or passage.get("source_document_id") != document_id:
                raise ValueError("pipeline methodology lineage has an unknown or cross-document passage")

    captured_at = _latest_timestamp(document_list)
    source_summary = "; ".join(
        f"{str(item.get('title', '')).strip()} — {str(item.get('final_url', '')).strip()}"
        for item in sorted(document_list, key=lambda value: str(value.get("source_id", "")))
    )
    providers = ", ".join(sorted({
        str(item.get("provider", "")).strip()
        for item in document_list
        if str(item.get("provider", "")).strip()
    }))
    subject = {"type": "project", "id": project_name}
    common_provenance = {
        "analyzer": "pipeline_methodology",
        "analyzer_version": METHOD_VERSION,
        "method": METHOD,
    }

    values = {
        ("source_identity", "source"): {
            "type": "text",
            "data": f"Source identity is recorded in source-documents.json: {source_summary}",
        },
        ("source_identity", "provider"): {
            "type": "text",
            "data": f"Source provider labels recorded in source-documents.json: {providers}",
        },
        ("provenance_fact", "method"): {
            "type": "text",
            "data": "The pipeline accepts claim candidates only after deterministic source-document, passage-binding, schema, and Expected Claim Map validation, then converts accepted passage-bound material into canonical Evidence.",
        },
        ("provenance_fact", "analyzer"): {
            "type": "text",
            "data": "passage_bound_evidence",
        },
        ("provenance_fact", "analyzer_version"): {
            "type": "text",
            "data": "v1",
        },
        ("lineage_fact", "evidence_lineage"): {
            "type": "text",
            "data": "Source Document -> Extracted Passage -> Claim Candidate -> Passage-Bound Source Material -> Canonical Evidence; every canonical evidence_id is indexed to its source_document_id and passage_ids in passage-bound-evidence-lineage.json.",
        },
        ("evidence_status", "status"): {
            "type": "categorical",
            "data": "active",
        },
    }

    records = []
    for claim_type, attribute, artifact in _PIPELINE_CLAIMS:
        source = {
            "type": "research_artifact",
            "source_id": f"research-artifact:{project_name}/{artifact}",
            "provider": "irl-ai-core",
            "retrieved_at": captured_at,
        }
        records.append(
            build_observation(
                report_id=report_id,
                domain="pipeline_methodology",
                subject=subject,
                claim={"type": claim_type, "attribute": attribute},
                value=values[(claim_type, attribute)],
                source=source,
                provenance=common_provenance,
                confidence=1.0,
                captured_at=captured_at,
            )
        )

    records.sort(key=lambda item: item["evidence_id"])
    errors = [
        error
        for record in records
        for error in _EVIDENCE_VALIDATOR.iter_errors(record)
    ]
    if errors:
        raise ValueError(f"Invalid pipeline methodology Evidence: {errors[0].message}")

    _save_if_changed(root, records)
    return records
