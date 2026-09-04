from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "alt-text.schema.json"


def _valid_contract() -> dict:
    return {
        "alt_text_id": "alt_1234567890abcdef",
        "brief_id": "brief_1",
        "report_id": "report_1",
        "decision_id": "decision_1",
        "strategy_id": "strategy_1",
        "config_id": "config_1",
        "draft_id": "draft_1",
        "image_spec_id": "imgspec_1234567890abcdef",
        "schema_version": "1.0",
        "lifecycle_stage": "alt_text_ready",
        "alt_texts": [{
            "image_id": "image_1234567890abcdef",
            "section_index": 0,
            "section_heading": "Introduction",
            "alt_text": "Consultant reviewing insurance documents at a desk",
            "status": "ready",
        }],
        "constraints": {
            "network_access": False,
            "provider_call": False,
            "image_analysis_call": False,
            "keyword_stuffing": False,
            "image_spec_mutation": False,
        },
        "audit": {
            "method": "article_image_context_to_informative_alt_text",
            "version": "v1",
            "validation_status": "validated",
        },
    }


def _validate(document: dict) -> list:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return list(Draft202012Validator(schema).iter_errors(document))


def test_valid_contract_matches_schema():
    assert _validate(_valid_contract()) == []


def test_required_lineage_and_image_reference_are_enforced():
    document = _valid_contract()
    del document["image_spec_id"]
    assert _validate(document)


def test_alt_texts_are_required_and_non_empty():
    document = _valid_contract()
    document["alt_texts"] = []
    assert _validate(document)


def test_alt_text_is_bounded_for_accessibility_metadata():
    document = _valid_contract()
    document["alt_texts"][0]["alt_text"] = "x" * 251
    assert _validate(document)


def test_alt_text_must_be_ready_in_phase_nine():
    document = _valid_contract()
    document["alt_texts"][0]["status"] = "pending"
    assert _validate(document)


def test_network_provider_and_image_analysis_calls_are_forbidden():
    document = _valid_contract()
    document["constraints"]["image_analysis_call"] = True
    assert _validate(document)


def test_keyword_stuffing_and_image_spec_mutation_are_forbidden():
    document = _valid_contract()
    document["constraints"]["keyword_stuffing"] = True
    assert _validate(document)


def test_unknown_properties_are_rejected():
    document = _valid_contract()
    document["model"] = "some-model"
    assert _validate(document)


def test_contract_fixture_can_be_copied_without_mutation():
    document = _valid_contract()
    before = copy.deepcopy(document)
    assert _validate(document) == []
    assert document == before
