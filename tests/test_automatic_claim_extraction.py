from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from agents.research.automatic_claim_extraction import (
    CLAIM_CANDIDATES_FILE,
    PASSAGE_BOUND_SOURCE_MATERIAL_FILE,
    run_automatic_claim_extraction,
)


ROOT = Path(__file__).resolve().parents[1]


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((ROOT / "shared" / "schemas" / filename).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _corpus(tmp_path: Path) -> tuple[Path, dict, dict]:
    root = tmp_path / "research" / "sample"
    root.mkdir(parents=True)

    html = "<html><body><main><p>Coverage includes hospital care.</p><p>Premiums vary by age.</p></main></body></html>"
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

    (root / "source-documents.json").write_text(json.dumps(documents, indent=2), encoding="utf-8")
    (root / "extracted-passages.json").write_text(json.dumps(passages, indent=2), encoding="utf-8")
    return root, documents, passages


def _candidate(document_id: str, *, passage_ids: list[str] | None = None, claim_type: str = "coverage_fact", attribute: str = "coverage") -> dict:
    return {
        "candidate_id": "cand_1",
        "source": {
            "source_id": "src_a",
            "source_document_id": document_id,
            "passage_ids": passage_ids or ["pass_a"],
        },
        "claim": {"type": claim_type, "attribute": attribute},
        "subject": {"type": "keyword", "id": "sample topic"},
        "value": {"type": "text", "data": "Coverage includes hospital care."},
        "confidence": 0.95,
        "relation": "supports",
    }


class RecordingProvider:
    def __init__(self, candidate_payload: dict):
        self.candidate_payload = candidate_payload
        self.calls = 0
        self.seen_source_documents: dict | None = None

    def extract_claims(self, *, project_name: str, source_documents: dict, extracted_passages: dict) -> dict:
        assert project_name == "sample"
        self.calls += 1
        self.seen_source_documents = source_documents
        assert "html" not in source_documents["documents"][0]
        assert "normalized_text" not in source_documents["documents"][0]
        source_documents["documents"][0]["provider"] = "mutated-inside-provider"
        return self.candidate_payload


def test_injected_provider_runs_behind_deterministic_gate_and_persists_outputs(tmp_path):
    root, documents, passages = _corpus(tmp_path)
    payload = {
        "schema_version": "1.0",
        "project_name": "sample",
        "candidates": [_candidate(documents["documents"][0]["source_document_id"])],
    }
    provider = RecordingProvider(payload)

    result = run_automatic_claim_extraction("sample", provider=provider, project_root=root)

    assert provider.calls == 1
    assert result["candidates"] == payload
    assert result["passage_bound_source_material"]["sources"][0]["facts"][0]["passage_ids"] == ["pass_a"]
    _validator("source-backed-claim-candidate.schema.json").validate(result["candidates"])
    _validator("passage-bound-source-material.schema.json").validate(result["passage_bound_source_material"])

    stored_candidates = json.loads((root / CLAIM_CANDIDATES_FILE).read_text(encoding="utf-8"))
    stored_material = json.loads((root / PASSAGE_BOUND_SOURCE_MATERIAL_FILE).read_text(encoding="utf-8"))
    assert stored_candidates == payload
    assert stored_material == result["passage_bound_source_material"]

    persisted_documents = json.loads((root / "source-documents.json").read_text(encoding="utf-8"))
    assert persisted_documents["documents"][0]["provider"] == "Example"


def test_provider_is_required_and_no_artifacts_are_written(tmp_path):
    root, _, _ = _corpus(tmp_path)

    with pytest.raises(ValueError, match="explicitly injected provider"):
        run_automatic_claim_extraction("sample", provider=None, project_root=root)

    assert not (root / CLAIM_CANDIDATES_FILE).exists()
    assert not (root / PASSAGE_BOUND_SOURCE_MATERIAL_FILE).exists()


def test_invalid_provider_output_fails_closed_before_writes(tmp_path):
    root, documents, _ = _corpus(tmp_path)
    candidate = _candidate(documents["documents"][0]["source_document_id"])
    del candidate["source"]["passage_ids"]
    payload = {"schema_version": "1.0", "project_name": "sample", "candidates": [candidate]}

    with pytest.raises(ValueError, match="Invalid source-backed claim candidates"):
        run_automatic_claim_extraction(
            "sample",
            provider=RecordingProvider(payload),
            project_root=root,
        )

    assert not (root / CLAIM_CANDIDATES_FILE).exists()
    assert not (root / PASSAGE_BOUND_SOURCE_MATERIAL_FILE).exists()


def test_signal_claim_is_rejected_by_claim_map_gate(tmp_path):
    root, documents, _ = _corpus(tmp_path)
    candidate = _candidate(
        documents["documents"][0]["source_document_id"],
        claim_type="query_intent",
        attribute="primary_intent",
    )
    payload = {"schema_version": "1.0", "project_name": "sample", "candidates": [candidate]}

    with pytest.raises(ValueError, match="not allowed by Expected Claim Map"):
        run_automatic_claim_extraction(
            "sample",
            provider=RecordingProvider(payload),
            project_root=root,
        )


def test_unknown_passage_is_rejected_fail_closed(tmp_path):
    root, documents, _ = _corpus(tmp_path)
    candidate = _candidate(
        documents["documents"][0]["source_document_id"],
        passage_ids=["missing"],
    )
    payload = {"schema_version": "1.0", "project_name": "sample", "candidates": [candidate]}

    with pytest.raises(ValueError, match="unknown passage_id"):
        run_automatic_claim_extraction(
            "sample",
            provider=RecordingProvider(payload),
            project_root=root,
        )


def test_cross_document_passage_binding_is_rejected(tmp_path):
    root, documents, passages = _corpus(tmp_path)
    document_id = documents["documents"][0]["source_document_id"]
    other_document_id = "doc_other"
    other_html = "<html><body><main><p>Other source.</p></main></body></html>"
    other_sha = hashlib.sha256(other_html.encode("utf-8")).hexdigest()
    documents["documents"].append({
        **documents["documents"][0],
        "source_document_id": other_document_id,
        "source_id": "src_b",
        "content_sha256": other_sha,
        "html": other_html,
        "content_bytes": len(other_html.encode("utf-8")),
        "normalized_text": "Other source.",
        "title": "Other",
    })
    passages["passages"].append({
        "passage_id": "pass_other",
        "source_document_id": other_document_id,
        "ordinal": 0,
        "kind": "paragraph",
        "heading_path": [],
        "text": "Other source.",
        "text_sha256": hashlib.sha256(b"Other source.").hexdigest(),
        "char_start": 0,
        "char_end": len("Other source."),
    })
    (root / "source-documents.json").write_text(json.dumps(documents, indent=2), encoding="utf-8")
    (root / "extracted-passages.json").write_text(json.dumps(passages, indent=2), encoding="utf-8")

    candidate = _candidate(document_id, passage_ids=["pass_a", "pass_other"])
    payload = {"schema_version": "1.0", "project_name": "sample", "candidates": [candidate]}

    with pytest.raises(ValueError, match="mixes source documents"):
        run_automatic_claim_extraction(
            "sample",
            provider=RecordingProvider(payload),
            project_root=root,
        )

    assert not (root / CLAIM_CANDIDATES_FILE).exists()
    assert not (root / PASSAGE_BOUND_SOURCE_MATERIAL_FILE).exists()


def test_provider_return_is_deep_copied_before_persistence(tmp_path):
    root, documents, _ = _corpus(tmp_path)
    payload = {
        "schema_version": "1.0",
        "project_name": "sample",
        "candidates": [_candidate(documents["documents"][0]["source_document_id"])],
    }
    provider = RecordingProvider(payload)

    result = run_automatic_claim_extraction("sample", provider=provider, project_root=root)
    result["candidates"]["candidates"][0]["candidate_id"] = "mutated-after-run"

    stored = json.loads((root / CLAIM_CANDIDATES_FILE).read_text(encoding="utf-8"))
    assert stored["candidates"][0]["candidate_id"] == "cand_1"
