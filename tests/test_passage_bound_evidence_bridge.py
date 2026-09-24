from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from agents.research.evidence.passage_bound import (
    CANONICAL_EVIDENCE_LINEAGE_FILE,
    SUBSTANTIVE_EVIDENCE_FILE,
    build_canonical_evidence_from_file,
    build_canonical_evidence_from_passage_bound_material,
)

ROOT = Path(__file__).resolve().parents[1]


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _corpus(tmp_path: Path):
    root = tmp_path / "research" / "sample"
    root.mkdir(parents=True)

    request_fingerprint = "a" * 64
    document_id = "doc_" + "1" * 24
    text_a = "International plans can include hospital care."
    text_b = "Age can affect premium cost."
    documents = {
        "schema_version": "1.1",
        "project_name": "sample",
        "request_fingerprint": request_fingerprint,
        "acquisition_policy_version": "1.1",
        "extraction_policy_version": "1.0",
        "documents": [{
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
            "content_sha256": _sha("<html><p>x</p></html>"),
            "content_bytes": len("<html><p>x</p></html>".encode("utf-8")),
            "redirect_chain": ["https://example.com/guide"],
            "etag": None,
            "last_modified": None,
            "html": "<html><p>x</p></html>",
            "title": "Guide",
            "normalized_text": "x",
        }],
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
                "text": text_a,
                "text_sha256": _sha(text_a),
                "char_start": 0,
                "char_end": len(text_a),
            },
            {
                "passage_id": "pass_b",
                "source_document_id": document_id,
                "ordinal": 1,
                "kind": "paragraph",
                "heading_path": [],
                "text": text_b,
                "text_sha256": _sha(text_b),
                "char_start": 0,
                "char_end": len(text_b),
            },
        ],
    }
    material = {
        "schema_version": "1.0",
        "project_name": "sample",
        "request_fingerprint": request_fingerprint,
        "acquisition_policy_version": "1.1",
        "extraction_policy_version": "1.0",
        "sources": [{
            "source_id": "src_a",
            "source_document_id": document_id,
            "url": "https://example.com/guide",
            "provider": "Example",
            "type": "official",
            "retrieved_at": "2026-09-24T10:00:00+00:00",
            "title": "Guide",
            "facts": [
                {
                    "candidate_id": "cand_coverage",
                    "source_id": "src_a",
                    "source_document_id": document_id,
                    "passage_ids": ["pass_a"],
                    "claim_type": "coverage_fact",
                    "attribute": "coverage",
                    "subject": {"type": "keyword", "id": "sample topic"},
                    "value": {"type": "text", "data": "Hospital care can be included."},
                    "confidence": 0.95,
                    "relation": "supports",
                },
                {
                    "candidate_id": "cand_premium",
                    "source_id": "src_a",
                    "source_document_id": document_id,
                    "passage_ids": ["pass_b"],
                    "claim_type": "pricing_factor",
                    "attribute": "cost_driver",
                    "subject": {"type": "keyword", "id": "sample topic"},
                    "value": {"type": "text", "data": "Age can affect premium cost."},
                    "confidence": 0.92,
                    "relation": "supports",
                },
            ],
        }],
    }
    return root, documents, passages, material


def test_bridge_emits_canonical_evidence_and_explicit_lineage(tmp_path):
    _, documents, passages, material = _corpus(tmp_path)

    records, lineage = build_canonical_evidence_from_passage_bound_material(
        report_id="rr_sample",
        material=material,
        source_documents=documents,
        extracted_passages=passages,
    )

    assert len(records) == 2
    assert all(record["type"] == "observation" for record in records)
    assert all(record["status"] == "active" for record in records)
    assert all(record["derived_from"] == [] for record in records)
    assert {record["relation"] for record in records} == {"supports"}

    evidence_schema = json.loads(
        (ROOT / "shared" / "schemas" / "evidence.schema.json").read_text()
    )
    evidence_validator = Draft202012Validator(
        evidence_schema,
        format_checker=FormatChecker(),
    )
    for record in records:
        evidence_validator.validate(record)

    lineage_schema = json.loads(
        (ROOT / "shared" / "schemas" / "canonical-evidence-lineage.schema.json").read_text()
    )
    Draft202012Validator(
        lineage_schema,
        format_checker=FormatChecker(),
    ).validate(lineage)

    by_candidate = {item["candidate_id"]: item for item in lineage["bindings"]}
    assert by_candidate["cand_coverage"]["source_document_id"] == "doc_" + "1" * 24
    assert by_candidate["cand_coverage"]["passage_ids"] == ["pass_a"]
    assert by_candidate["cand_premium"]["passage_ids"] == ["pass_b"]
    assert set(lineage["evidence_ids"]) == {record["evidence_id"] for record in records}


def test_bridge_rejects_unknown_passage_and_claim_map_breach(tmp_path):
    _, documents, passages, material = _corpus(tmp_path)

    material["sources"][0]["facts"][0]["passage_ids"] = ["missing"]
    with pytest.raises(ValueError, match="unknown passage_id"):
        build_canonical_evidence_from_passage_bound_material(
            report_id="rr_sample",
            material=material,
            source_documents=documents,
            extracted_passages=passages,
        )

    material["sources"][0]["facts"][0]["passage_ids"] = ["pass_a"]
    material["sources"][0]["facts"][0]["claim_type"] = "query_intent"
    material["sources"][0]["facts"][0]["attribute"] = "primary_intent"
    with pytest.raises(ValueError, match="Expected Claim Map"):
        build_canonical_evidence_from_passage_bound_material(
            report_id="rr_sample",
            material=material,
            source_documents=documents,
            extracted_passages=passages,
        )


def test_bridge_rejects_source_metadata_mismatch(tmp_path):
    _, documents, passages, material = _corpus(tmp_path)
    material["sources"][0]["provider"] = "wrong-provider"

    with pytest.raises(ValueError, match="provider does not match source document"):
        build_canonical_evidence_from_passage_bound_material(
            report_id="rr_sample",
            material=material,
            source_documents=documents,
            extracted_passages=passages,
        )


def test_bridge_rejects_cross_document_passage_binding(tmp_path):
    _, documents, passages, material = _corpus(tmp_path)
    other_id = "doc_" + "2" * 24

    passages["passages"].append({
        **passages["passages"][0],
        "passage_id": "pass_other",
        "source_document_id": other_id,
    })
    material["sources"][0]["facts"][0]["passage_ids"] = ["pass_a", "pass_other"]

    with pytest.raises(ValueError, match="mixes source documents"):
        build_canonical_evidence_from_passage_bound_material(
            report_id="rr_sample",
            material=material,
            source_documents=documents,
            extracted_passages=passages,
        )


def test_evidence_ids_include_source_lineage_context(tmp_path):
    _, documents, passages, material = _corpus(tmp_path)

    first, _ = build_canonical_evidence_from_passage_bound_material(
        report_id="rr_sample",
        material=material,
        source_documents=documents,
        extracted_passages=passages,
    )

    other_id = "doc_" + "2" * 24
    documents["documents"].append({
        **documents["documents"][0],
        "source_document_id": other_id,
        "source_id": "src_b",
        "requested_url": "https://example.com/other",
        "final_url": "https://example.com/other",
        "provider": "Other",
        "content_sha256": _sha("<html><p>other</p></html>"),
        "content_bytes": len("<html><p>other</p></html>".encode("utf-8")),
        "title": "Other",
        "normalized_text": "other",
        "html": "<html><p>other</p></html>",
    })
    passages["passages"].append({
        **passages["passages"][0],
        "passage_id": "pass_other",
        "source_document_id": other_id,
    })

    material["sources"].append({
        **material["sources"][0],
        "source_id": "src_b",
        "source_document_id": other_id,
        "url": "https://example.com/other",
        "provider": "Other",
        "title": "Other",
        "facts": [{
            **material["sources"][0]["facts"][0],
            "candidate_id": "cand_same_claim_other_source",
            "source_id": "src_b",
            "source_document_id": other_id,
            "passage_ids": ["pass_other"],
        }],
    })

    second, _ = build_canonical_evidence_from_passage_bound_material(
        report_id="rr_sample",
        material=material,
        source_documents=documents,
        extracted_passages=passages,
    )

    first_ids = {record["evidence_id"] for record in first}
    second_ids = {record["evidence_id"] for record in second}
    assert len(second_ids) == 3
    assert len(first_ids & second_ids) == 2
    assert len(second_ids - first_ids) == 1


def test_file_bridge_writes_canonical_evidence_and_lineage(tmp_path):
    root, documents, passages, material = _corpus(tmp_path)
    (root / "source-documents.json").write_text(
        json.dumps(documents, indent=2),
        encoding="utf-8",
    )
    (root / "extracted-passages.json").write_text(
        json.dumps(passages, indent=2),
        encoding="utf-8",
    )
    (root / "passage-bound-source-material.json").write_text(
        json.dumps(material, indent=2),
        encoding="utf-8",
    )

    records = build_canonical_evidence_from_file(
        report_id="rr_sample",
        project_path=root,
    )

    assert json.loads(
        (root / SUBSTANTIVE_EVIDENCE_FILE).read_text()
    ) == records
    assert (root / CANONICAL_EVIDENCE_LINEAGE_FILE).exists()


def test_file_bridge_requires_corpus_and_does_not_fallback(tmp_path):
    root, _, _, material = _corpus(tmp_path)
    (root / "passage-bound-source-material.json").write_text(
        json.dumps(material),
        encoding="utf-8",
    )
    (root / "source-material.json").write_text(
        json.dumps(material),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="source-documents.json"):
        build_canonical_evidence_from_file(
            report_id="rr_sample",
            project_path=root,
        )
