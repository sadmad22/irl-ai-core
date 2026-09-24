from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from agents.research.claim_extraction import (
    build_passage_bound_source_material,
    validate_claim_candidates,
)


ROOT = Path(__file__).resolve().parents[1]


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((ROOT / "shared" / "schemas" / filename).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _corpus() -> tuple[dict, dict]:
    html = "<html><head><title>Guide</title></head><body><main><p>Coverage includes hospital care.</p><p>Premiums vary by age.</p></main></body></html>"
    content_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    document_id = "doc_" + content_sha[:24]
    request_fingerprint = "a" * 64
    first_text = "Coverage includes hospital care."
    second_text = "Premiums vary by age."

    documents = {
        "schema_version": "1.1",
        "project_name": "sample",
        "request_fingerprint": request_fingerprint,
        "acquisition_policy_version": "1.1",
        "extraction_policy_version": "1.0",
        "documents": [
            {
                "source_document_id": document_id,
                "source_id": "src_a",
                "requested_url": "https://example.com/guide",
                "final_url": "https://example.com/guide",
                "provider": "Example",
                "type": "official",
                "retrieved_at": "2026-09-24T10:00:00+00:00",
                "cache_checked_at": "2026-09-24T10:00:00+00:00",
                "http_status": 200,
                "content_type": "text/html",
                "content_sha256": content_sha,
                "content_bytes": len(html.encode("utf-8")),
                "redirect_chain": ["https://example.com/guide"],
                "etag": None,
                "last_modified": None,
                "html": html,
                "title": "Guide",
                "normalized_text": first_text + "\n" + second_text,
            }
        ],
    }

    passages = {
        "schema_version": "1.1",
        "project_name": "sample",
        "request_fingerprint": request_fingerprint,
        "acquisition_policy_version": "1.1",
        "extraction_policy_version": "1.0",
        "passages": [
            {
                "passage_id": "pass_a",
                "source_document_id": document_id,
                "ordinal": 0,
                "kind": "paragraph",
                "heading_path": [],
                "text": first_text,
                "text_sha256": hashlib.sha256(first_text.encode("utf-8")).hexdigest(),
                "char_start": 0,
                "char_end": len(first_text),
            },
            {
                "passage_id": "pass_b",
                "source_document_id": document_id,
                "ordinal": 1,
                "kind": "paragraph",
                "heading_path": [],
                "text": second_text,
                "text_sha256": hashlib.sha256(second_text.encode("utf-8")).hexdigest(),
                "char_start": len(first_text) + 1,
                "char_end": len(first_text) + 1 + len(second_text),
            },
        ],
    }
    return documents, passages


def _candidate(
    *,
    candidate_id: str = "cand_1",
    source_id: str = "src_a",
    source_document_id: str | None = None,
    passage_ids: list[str] | None = None,
    claim_type: str = "coverage_fact",
    attribute: str = "coverage",
) -> dict:
    documents, _ = _corpus()
    return {
        "candidate_id": candidate_id,
        "source": {
            "source_id": source_id,
            "source_document_id": source_document_id or documents["documents"][0]["source_document_id"],
            "passage_ids": passage_ids or ["pass_a"],
        },
        "claim": {"type": claim_type, "attribute": attribute},
        "subject": {"type": "keyword", "id": "sample topic"},
        "value": {"type": "text", "data": "Coverage includes hospital care."},
        "confidence": 0.95,
        "relation": "supports",
    }


def _candidates(*items: dict) -> dict:
    return {
        "schema_version": "1.0",
        "project_name": "sample",
        "candidates": list(items),
    }


def test_candidate_schema_requires_passage_binding():
    candidates = _candidates(_candidate())
    _validator("source-backed-claim-candidate.schema.json").validate(candidates)

    missing_binding = _candidate()
    del missing_binding["source"]["passage_ids"]

    with pytest.raises(Exception):
        _validator("source-backed-claim-candidate.schema.json").validate(
            _candidates(missing_binding)
        )


def test_valid_candidate_builds_auditable_passage_bound_material():
    documents, passages = _corpus()

    material = build_passage_bound_source_material(
        candidates=_candidates(_candidate()),
        source_documents=documents,
        extracted_passages=passages,
    )

    _validator("passage-bound-source-material.schema.json").validate(material)

    fact = material["sources"][0]["facts"][0]
    assert fact["candidate_id"] == "cand_1"
    assert fact["source_id"] == "src_a"
    assert fact["source_document_id"] == documents["documents"][0]["source_document_id"]
    assert fact["passage_ids"] == ["pass_a"]
    assert fact["claim_type"] == "coverage_fact"
    assert fact["attribute"] == "coverage"


def test_unknown_passage_is_rejected_fail_closed():
    documents, passages = _corpus()
    candidate = _candidate(passage_ids=["missing_passage"])

    with pytest.raises(ValueError, match="unknown passage_id"):
        validate_claim_candidates(
            _candidates(candidate),
            source_documents=documents,
            extracted_passages=passages,
        )


def test_passages_from_different_documents_cannot_be_mixed():
    documents, passages = _corpus()
    document_id = documents["documents"][0]["source_document_id"]
    other_document_id = "doc_other"
    other_text = "A second source says the same thing."

    passages["passages"].append(
        {
            "passage_id": "pass_other",
            "source_document_id": other_document_id,
            "ordinal": 0,
            "kind": "paragraph",
            "heading_path": [],
            "text": other_text,
            "text_sha256": hashlib.sha256(other_text.encode("utf-8")).hexdigest(),
            "char_start": 0,
            "char_end": len(other_text),
        }
    )

    candidate = _candidate(
        source_document_id=document_id,
        passage_ids=["pass_a", "pass_other"],
    )

    with pytest.raises(ValueError, match="mixes source documents"):
        validate_claim_candidates(
            _candidates(candidate),
            source_documents=documents,
            extracted_passages=passages,
        )


def test_source_id_must_match_source_document():
    documents, passages = _corpus()
    candidate = _candidate(source_id="src_wrong")

    with pytest.raises(ValueError, match="source_id does not match source document"):
        validate_claim_candidates(
            _candidates(candidate),
            source_documents=documents,
            extracted_passages=passages,
        )


def test_unknown_source_document_is_rejected():
    documents, passages = _corpus()
    candidate = _candidate(source_document_id="doc_missing")

    with pytest.raises(ValueError, match="unknown source_document_id"):
        validate_claim_candidates(
            _candidates(candidate),
            source_documents=documents,
            extracted_passages=passages,
        )


@pytest.mark.parametrize(
    ("claim_type", "attribute"),
    [
        ("query_intent", "primary_intent"),
        ("authority", "authority_score"),
        ("entity_presence", "mentioned"),
    ],
)
def test_signal_claims_are_not_accepted_as_substantive_candidates(claim_type, attribute):
    documents, passages = _corpus()
    candidate = _candidate(claim_type=claim_type, attribute=attribute)

    with pytest.raises(ValueError, match="not allowed by Expected Claim Map"):
        validate_claim_candidates(
            _candidates(candidate),
            source_documents=documents,
            extracted_passages=passages,
        )


def test_duplicate_candidate_ids_are_rejected():
    documents, passages = _corpus()
    first = _candidate(candidate_id="dup")
    second = _candidate(candidate_id="dup", passage_ids=["pass_b"])

    with pytest.raises(ValueError, match="duplicate candidate_id"):
        validate_claim_candidates(
            _candidates(first, second),
            source_documents=documents,
            extracted_passages=passages,
        )


def test_corpus_identity_mismatch_is_rejected():
    documents, passages = _corpus()
    passages["request_fingerprint"] = "b" * 64

    with pytest.raises(ValueError, match="different corpus identities"):
        validate_claim_candidates(
            _candidates(_candidate()),
            source_documents=documents,
            extracted_passages=passages,
        )


def test_output_is_deterministic_and_sorted_by_document_then_candidate():
    documents, passages = _corpus()
    first = _candidate(candidate_id="b", passage_ids=["pass_b"])
    second = _candidate(candidate_id="a", passage_ids=["pass_a"])

    material_one = build_passage_bound_source_material(
        candidates=_candidates(first, second),
        source_documents=documents,
        extracted_passages=passages,
    )
    material_two = build_passage_bound_source_material(
        candidates=_candidates(second, first),
        source_documents=documents,
        extracted_passages=passages,
    )

    assert material_one == material_two
    assert [fact["candidate_id"] for fact in material_one["sources"][0]["facts"]] == ["a", "b"]
