from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .expected_claim_map import EXPECTED_CLAIM_MAP


SCHEMA_VERSION = "1.0"
PASSAGE_BOUND_SOURCE_MATERIAL_SCHEMA_VERSION = "1.0"

_ROOT = Path(__file__).resolve().parents[2]


def _load_validator(filename: str) -> Draft202012Validator:
    schema = json.loads(
        (_ROOT / "shared" / "schemas" / filename).read_text(encoding="utf-8")
    )
    return Draft202012Validator(schema, format_checker=FormatChecker())


_CANDIDATE_VALIDATOR = _load_validator("source-backed-claim-candidate.schema.json")
_BOUND_MATERIAL_VALIDATOR = _load_validator("passage-bound-source-material.schema.json")
_DOCUMENTS_VALIDATOR = _load_validator("source-documents.schema.json")
_PASSAGES_VALIDATOR = _load_validator("extracted-passages.schema.json")


def _validate(
    validator: Draft202012Validator,
    payload: dict[str, Any],
    label: str,
) -> None:
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(item) for item in errors[0].path) or "<root>"
        raise ValueError(
            f"Invalid {label} at {location}: {errors[0].message}"
        )


def _allowed_substantive_claims() -> set[tuple[str, str]]:
    allowed: set[tuple[str, str]] = set()
    for section in EXPECTED_CLAIM_MAP.values():
        for item in (*section["required_claims"], *section["supporting_claims"]):
            if item["evidence_kind"] == "substantive":
                allowed.add((item["claim_type"], item["attribute"]))
    return allowed


_ALLOWED_SUBSTANTIVE_CLAIMS = _allowed_substantive_claims()


def validate_claim_candidates(
    candidates: dict[str, Any],
    *,
    source_documents: dict[str, Any],
    extracted_passages: dict[str, Any],
) -> None:
    """Validate proposed claims against the extracted source corpus.

    The candidate provider is intentionally outside this function. This validator
    is the acceptance gate and fails closed on any broken source or passage binding.
    """
    if not isinstance(candidates, dict):
        raise TypeError("candidates must be a dictionary")
    if not isinstance(source_documents, dict):
        raise TypeError("source_documents must be a dictionary")
    if not isinstance(extracted_passages, dict):
        raise TypeError("extracted_passages must be a dictionary")

    _validate(_CANDIDATE_VALIDATOR, candidates, "source-backed claim candidates")
    _validate(_DOCUMENTS_VALIDATOR, source_documents, "source documents")
    _validate(_PASSAGES_VALIDATOR, extracted_passages, "extracted passages")

    if candidates["project_name"] != source_documents["project_name"]:
        raise ValueError("claim candidates project_name does not match source documents")
    if candidates["project_name"] != extracted_passages["project_name"]:
        raise ValueError("claim candidates project_name does not match extracted passages")
    if source_documents["request_fingerprint"] != extracted_passages["request_fingerprint"]:
        raise ValueError("source documents and extracted passages have different corpus identities")
    if source_documents["acquisition_policy_version"] != extracted_passages["acquisition_policy_version"]:
        raise ValueError("source documents and extracted passages have different acquisition policies")
    if source_documents["extraction_policy_version"] != extracted_passages["extraction_policy_version"]:
        raise ValueError("source documents and extracted passages have different extraction policies")

    documents_by_id: dict[str, dict[str, Any]] = {}
    for document in source_documents["documents"]:
        document_id = document["source_document_id"]
        if document_id in documents_by_id:
            raise ValueError(f"duplicate source_document_id: {document_id}")
        documents_by_id[document_id] = document

    passages_by_id: dict[str, dict[str, Any]] = {}
    for passage in extracted_passages["passages"]:
        passage_id = passage["passage_id"]
        if passage_id in passages_by_id:
            raise ValueError(f"duplicate passage_id: {passage_id}")
        passages_by_id[passage_id] = passage

    seen_candidate_ids: set[str] = set()
    for candidate in candidates["candidates"]:
        candidate_id = candidate["candidate_id"]
        if candidate_id in seen_candidate_ids:
            raise ValueError(f"duplicate candidate_id: {candidate_id}")
        seen_candidate_ids.add(candidate_id)

        claim_type = candidate["claim"]["type"]
        attribute = candidate["claim"]["attribute"]
        if (claim_type, attribute) not in _ALLOWED_SUBSTANTIVE_CLAIMS:
            raise ValueError(
                "Claim Candidate is not allowed by Expected Claim Map: "
                f"{claim_type}.{attribute}"
            )

        binding = candidate["source"]
        source_id = binding["source_id"]
        source_document_id = binding["source_document_id"]
        document = documents_by_id.get(source_document_id)
        if document is None:
            raise ValueError(
                f"Claim Candidate {candidate_id} references unknown source_document_id: "
                f"{source_document_id}"
            )

        if document["source_id"] != source_id:
            raise ValueError(
                f"Claim Candidate {candidate_id} source_id does not match source document"
            )

        passage_ids = binding["passage_ids"]
        for passage_id in passage_ids:
            passage = passages_by_id.get(passage_id)
            if passage is None:
                raise ValueError(
                    f"Claim Candidate {candidate_id} references unknown passage_id: "
                    f"{passage_id}"
                )
            if passage["source_document_id"] != source_document_id:
                raise ValueError(
                    f"Claim Candidate {candidate_id} mixes source documents across passage bindings"
                )


def build_passage_bound_source_material(
    *,
    candidates: dict[str, Any],
    source_documents: dict[str, Any],
    extracted_passages: dict[str, Any],
) -> dict[str, Any]:
    """Create deterministic, validated material with explicit passage lineage.

    No provider is called here and no claim text is generated or rewritten. The
    candidate payload is accepted only after deterministic contract validation.
    """
    validate_claim_candidates(
        candidates,
        source_documents=source_documents,
        extracted_passages=extracted_passages,
    )

    documents_by_id = {
        item["source_document_id"]: item
        for item in source_documents["documents"]
    }

    grouped: dict[str, list[dict[str, Any]]] = {}
    for candidate in sorted(
        candidates["candidates"],
        key=lambda item: (
            item["source"]["source_document_id"],
            item["candidate_id"],
        ),
    ):
        binding = candidate["source"]
        source_document_id = binding["source_document_id"]
        grouped.setdefault(source_document_id, []).append(
            {
                "candidate_id": candidate["candidate_id"],
                "source_id": binding["source_id"],
                "source_document_id": source_document_id,
                "passage_ids": sorted(binding["passage_ids"]),
                "claim_type": candidate["claim"]["type"],
                "attribute": candidate["claim"]["attribute"],
                "subject": candidate["subject"],
                "value": candidate["value"],
                "confidence": candidate["confidence"],
                "relation": candidate["relation"],
            }
        )

    sources: list[dict[str, Any]] = []
    for source_document_id in sorted(grouped):
        document = documents_by_id[source_document_id]
        sources.append(
            {
                "source_id": document["source_id"],
                "source_document_id": source_document_id,
                "url": document["final_url"],
                "provider": document["provider"],
                "type": document["type"],
                "retrieved_at": document["retrieved_at"],
                "title": document["title"],
                "facts": grouped[source_document_id],
            }
        )

    material = {
        "schema_version": PASSAGE_BOUND_SOURCE_MATERIAL_SCHEMA_VERSION,
        "project_name": candidates["project_name"],
        "request_fingerprint": source_documents["request_fingerprint"],
        "acquisition_policy_version": source_documents["acquisition_policy_version"],
        "extraction_policy_version": source_documents["extraction_policy_version"],
        "sources": sources,
    }
    _validate(
        _BOUND_MATERIAL_VALIDATOR,
        material,
        "passage-bound source material",
    )
    return material
