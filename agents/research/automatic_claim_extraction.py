from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Protocol

from .claim_extraction import (
    build_passage_bound_source_material,
    validate_claim_candidates,
)


CLAIM_CANDIDATES_FILE = "claim-candidates.json"
PASSAGE_BOUND_SOURCE_MATERIAL_FILE = "passage-bound-source-material.json"
SOURCE_DOCUMENTS_FILE = "source-documents.json"
EXTRACTED_PASSAGES_FILE = "extracted-passages.json"


class AutomaticClaimExtractionProviderProtocol(Protocol):
    def extract_claims(
        self,
        *,
        project_name: str,
        source_documents: dict[str, Any],
        extracted_passages: dict[str, Any],
    ) -> dict[str, Any]:
        ...


def _load_required(project_root: Path, filename: str) -> dict[str, Any]:
    path = project_root / filename
    if not path.exists():
        raise FileNotFoundError(f"{filename} not found")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{filename} is unreadable or invalid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{filename} must contain an object")
    return data


def _provider_context(source_documents: dict[str, Any]) -> dict[str, Any]:
    """Expose source identity to the provider without exposing raw source HTML."""
    return {
        "schema_version": source_documents["schema_version"],
        "project_name": source_documents["project_name"],
        "request_fingerprint": source_documents["request_fingerprint"],
        "acquisition_policy_version": source_documents["acquisition_policy_version"],
        "extraction_policy_version": source_documents["extraction_policy_version"],
        "documents": [
            {
                "source_document_id": document["source_document_id"],
                "source_id": document["source_id"],
                "requested_url": document["requested_url"],
                "final_url": document["final_url"],
                "provider": document["provider"],
                "type": document["type"],
                "retrieved_at": document["retrieved_at"],
                "content_sha256": document["content_sha256"],
                "title": document["title"],
            }
            for document in source_documents["documents"]
        ],
    }


def _call_provider(
    provider: AutomaticClaimExtractionProviderProtocol | Any,
    *,
    project_name: str,
    source_documents: dict[str, Any],
    extracted_passages: dict[str, Any],
) -> dict[str, Any]:
    if provider is None:
        raise ValueError("Automatic Claim Extraction requires an explicitly injected provider")
    extractor = getattr(provider, "extract_claims", None)
    if extractor is None or not callable(extractor):
        raise ValueError(
            "Automatic Claim Extraction provider must expose "
            "extract_claims(project_name=..., source_documents=..., extracted_passages=...)"
        )

    result = extractor(
        project_name=project_name,
        source_documents=copy.deepcopy(_provider_context(source_documents)),
        extracted_passages=copy.deepcopy(extracted_passages),
    )
    if not isinstance(result, dict):
        raise ValueError("Automatic Claim Extraction provider must return a candidate object")
    return copy.deepcopy(result)


def _save_if_changed(project_root: Path, filename: str, data: dict[str, Any]) -> None:
    path = project_root / filename
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if current != data:
        path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )


def run_automatic_claim_extraction(
    project_name: str,
    *,
    provider: AutomaticClaimExtractionProviderProtocol | Any,
    project_root: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Run an injected claim proposer behind the deterministic Claim Contract gate."""
    if not str(project_name).strip():
        raise ValueError("project_name is required")

    root = Path(project_root) if project_root is not None else Path("research") / project_name
    source_documents = _load_required(root, SOURCE_DOCUMENTS_FILE)
    extracted_passages = _load_required(root, EXTRACTED_PASSAGES_FILE)

    candidates = _call_provider(
        provider,
        project_name=project_name,
        source_documents=source_documents,
        extracted_passages=extracted_passages,
    )

    # Acceptance is deterministic and occurs before any artifact is written.
    validate_claim_candidates(
        candidates,
        source_documents=source_documents,
        extracted_passages=extracted_passages,
    )
    passage_bound_material = build_passage_bound_source_material(
        candidates=candidates,
        source_documents=source_documents,
        extracted_passages=extracted_passages,
    )

    _save_if_changed(root, CLAIM_CANDIDATES_FILE, candidates)
    _save_if_changed(root, PASSAGE_BOUND_SOURCE_MATERIAL_FILE, passage_bound_material)

    return {
        "candidates": candidates,
        "passage_bound_source_material": passage_bound_material,
    }
