from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from ..expected_claim_map import EXPECTED_CLAIM_MAP
from .domain_common import build_observation

PASSAGE_BOUND_SOURCE_MATERIAL_FILE = "passage-bound-source-material.json"
SUBSTANTIVE_EVIDENCE_FILE = "substantive-evidence.json"
CANONICAL_EVIDENCE_LINEAGE_FILE = "passage-bound-evidence-lineage.json"
SOURCE_DOCUMENTS_FILE = "source-documents.json"
EXTRACTED_PASSAGES_FILE = "extracted-passages.json"

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_ROOT = Path(__file__).resolve().parents[3]


def _load_validator(filename: str) -> Draft202012Validator:
    schema = json.loads(
        (_ROOT / "shared" / "schemas" / filename).read_text(encoding="utf-8")
    )
    return Draft202012Validator(schema, format_checker=FormatChecker())


_MATERIAL_VALIDATOR = _load_validator("passage-bound-source-material.schema.json")
_DOCUMENTS_VALIDATOR = _load_validator("source-documents.schema.json")
_PASSAGES_VALIDATOR = _load_validator("extracted-passages.schema.json")
_EVIDENCE_VALIDATOR = _load_validator("evidence.schema.json")
_LINEAGE_VALIDATOR = _load_validator("canonical-evidence-lineage.schema.json")


def _validate(validator: Draft202012Validator, payload: dict[str, Any], label: str) -> None:
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(item) for item in errors[0].path) or "<root>"
        raise ValueError(f"Invalid {label} at {location}: {errors[0].message}")


def _allowed_substantive_claims() -> set[tuple[str, str]]:
    allowed: set[tuple[str, str]] = set()
    for section in EXPECTED_CLAIM_MAP.values():
        for item in (*section["required_claims"], *section["supporting_claims"]):
            if item["evidence_kind"] == "substantive":
                allowed.add((item["claim_type"], item["attribute"]))
    return allowed


_ALLOWED_SUBSTANTIVE_CLAIMS = _allowed_substantive_claims()


def _evidence_id(
    *,
    report_id: str,
    candidate_id: str,
    source_document_id: str,
    passage_ids: list[str],
    claim: dict[str, Any],
    value: dict[str, Any],
) -> str:
    payload = {
        "report_id": report_id,
        "candidate_id": candidate_id,
        "source_document_id": source_document_id,
        "passage_ids": sorted(passage_ids),
        "claim": claim,
        "value": value,
        "schema_version": SCHEMA_VERSION,
    }
    digest = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()[:24]
    return f"ev_{digest}"


def _source_metadata(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": source["type"],
        "source_id": source["source_id"],
        "provider": source["provider"],
        "retrieved_at": source["retrieved_at"],
    }


def _provenance() -> dict[str, str]:
    return {
        "analyzer": "passage_bound_evidence",
        "analyzer_version": METHOD_VERSION,
        "method": "passage_bound_source_material_v1",
    }


def build_canonical_evidence_from_passage_bound_material(
    *,
    report_id: str,
    material: dict[str, Any],
    source_documents: dict[str, Any],
    extracted_passages: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Convert accepted Passage-Bound Source Material into canonical Evidence.

    The canonical Evidence schema remains unchanged. Detailed
    source-document/passage lineage is retained in a deterministic sidecar
    keyed by canonical evidence_id.
    """
    if not str(report_id).strip():
        raise ValueError("report_id is required")
    if not isinstance(material, dict):
        raise TypeError("material must be a dictionary")
    if not isinstance(source_documents, dict):
        raise TypeError("source_documents must be a dictionary")
    if not isinstance(extracted_passages, dict):
        raise TypeError("extracted_passages must be a dictionary")

    _validate(_MATERIAL_VALIDATOR, material, "passage-bound source material")
    _validate(_DOCUMENTS_VALIDATOR, source_documents, "source documents")
    _validate(_PASSAGES_VALIDATOR, extracted_passages, "extracted passages")

    if material["project_name"] != source_documents["project_name"]:
        raise ValueError("passage-bound material project_name does not match source documents")
    if material["project_name"] != extracted_passages["project_name"]:
        raise ValueError("passage-bound material project_name does not match extracted passages")

    for field in (
        "request_fingerprint",
        "acquisition_policy_version",
        "extraction_policy_version",
    ):
        value = material.get(field)
        if value is not None and value != source_documents[field]:
            raise ValueError(f"passage-bound material {field} does not match source documents")
        if value is not None and value != extracted_passages[field]:
            raise ValueError(f"passage-bound material {field} does not match extracted passages")

    documents_by_id = {
        document["source_document_id"]: document
        for document in source_documents["documents"]
    }
    passages_by_id = {
        passage["passage_id"]: passage
        for passage in extracted_passages["passages"]
    }

    records: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    seen_candidate_ids: set[str] = set()
    seen_evidence_ids: set[str] = set()

    for source in material["sources"]:
        document_id = source["source_document_id"]
        document = documents_by_id.get(document_id)
        if document is None:
            raise ValueError(
                f"passage-bound material references unknown source_document_id: {document_id}"
            )

        if source["source_id"] != document["source_id"]:
            raise ValueError(
                f"passage-bound material source_id does not match source document: {document_id}"
            )
        if source["url"] != document["final_url"]:
            raise ValueError(
                f"passage-bound material URL does not match source document: {document_id}"
            )
        if source["provider"] != document["provider"]:
            raise ValueError(
                f"passage-bound material provider does not match source document: {document_id}"
            )
        if source["type"] != document["type"]:
            raise ValueError(
                f"passage-bound material type does not match source document: {document_id}"
            )
        if source["retrieved_at"] != document["retrieved_at"]:
            raise ValueError(
                f"passage-bound material retrieved_at does not match source document: {document_id}"
            )
        if source["title"] != document["title"]:
            raise ValueError(
                f"passage-bound material title does not match source document: {document_id}"
            )

        for fact in source["facts"]:
            candidate_id = fact["candidate_id"]
            if candidate_id in seen_candidate_ids:
                raise ValueError(
                    f"duplicate candidate_id in passage-bound material: {candidate_id}"
                )
            seen_candidate_ids.add(candidate_id)

            if fact["source_id"] != source["source_id"]:
                raise ValueError(
                    f"fact source_id does not match source envelope: {candidate_id}"
                )
            if fact["source_document_id"] != document_id:
                raise ValueError(
                    f"fact source_document_id does not match source envelope: {candidate_id}"
                )

            passage_ids = sorted(fact["passage_ids"])
            for passage_id in passage_ids:
                passage = passages_by_id.get(passage_id)
                if passage is None:
                    raise ValueError(
                        f"candidate {candidate_id} references unknown passage_id: {passage_id}"
                    )
                if passage["source_document_id"] != document_id:
                    raise ValueError(
                        f"candidate {candidate_id} mixes source documents across passage bindings"
                    )

            claim = {
                "type": fact["claim_type"],
                "attribute": fact["attribute"],
            }
            pair = (claim["type"], claim["attribute"])
            if pair not in _ALLOWED_SUBSTANTIVE_CLAIMS:
                raise ValueError(
                    "Passage-bound claim is not allowed by Expected Claim Map: "
                    f"{claim['type']}.{claim['attribute']}"
                )

            evidence_id = _evidence_id(
                report_id=report_id,
                candidate_id=candidate_id,
                source_document_id=document_id,
                passage_ids=passage_ids,
                claim=claim,
                value=fact["value"],
            )
            if evidence_id in seen_evidence_ids:
                raise ValueError(f"duplicate canonical evidence_id: {evidence_id}")
            seen_evidence_ids.add(evidence_id)

            record = build_observation(
                report_id=report_id,
                domain=f"substantive_{claim['type']}",
                subject=fact["subject"],
                claim=claim,
                value=fact["value"],
                source=_source_metadata(source),
                provenance=_provenance(),
                confidence=fact["confidence"],
                captured_at=str(source["retrieved_at"]),
                evidence_id=evidence_id,
            )
            record["relation"] = fact["relation"]
            _validate(_EVIDENCE_VALIDATOR, record, "canonical Evidence")
            records.append(record)

            bindings.append(
                {
                    "evidence_id": evidence_id,
                    "candidate_id": candidate_id,
                    "source_id": fact["source_id"],
                    "source_document_id": document_id,
                    "passage_ids": passage_ids,
                }
            )

    records.sort(key=lambda item: item["evidence_id"])
    bindings.sort(key=lambda item: item["evidence_id"])

    lineage = {
        "schema_version": SCHEMA_VERSION,
        "project_name": material["project_name"],
        "request_fingerprint": material["request_fingerprint"],
        "acquisition_policy_version": material["acquisition_policy_version"],
        "extraction_policy_version": material["extraction_policy_version"],
        "bindings": bindings,
        "evidence_ids": [record["evidence_id"] for record in records],
    }
    _validate(_LINEAGE_VALIDATOR, lineage, "canonical Evidence lineage")

    return records, lineage


def build_canonical_evidence_from_file(
    *,
    report_id: str,
    project_path: str | Path,
) -> list[dict[str, Any]]:
    """Load E output, convert it to canonical Evidence, and persist its lineage."""
    project_root = Path(project_path)
    material_path = project_root / PASSAGE_BOUND_SOURCE_MATERIAL_FILE
    if not material_path.exists():
        raise FileNotFoundError(f"{PASSAGE_BOUND_SOURCE_MATERIAL_FILE} not found")

    source_documents_path = project_root / SOURCE_DOCUMENTS_FILE
    passages_path = project_root / EXTRACTED_PASSAGES_FILE
    if not source_documents_path.exists() or not passages_path.exists():
        raise FileNotFoundError(
            "Passage-bound Evidence requires source-documents.json and extracted-passages.json"
        )

    material = json.loads(material_path.read_text(encoding="utf-8"))
    source_documents = json.loads(source_documents_path.read_text(encoding="utf-8"))
    extracted_passages = json.loads(passages_path.read_text(encoding="utf-8"))

    records, lineage = build_canonical_evidence_from_passage_bound_material(
        report_id=report_id,
        material=material,
        source_documents=source_documents,
        extracted_passages=extracted_passages,
    )

    (project_root / SUBSTANTIVE_EVIDENCE_FILE).write_text(
        json.dumps(records, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    (project_root / CANONICAL_EVIDENCE_LINEAGE_FILE).write_text(
        json.dumps(lineage, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return records
