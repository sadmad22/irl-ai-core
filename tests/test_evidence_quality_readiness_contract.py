from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
READINESS_SCHEMA = json.loads(
    (ROOT / "shared" / "schemas" / "section-evidence-readiness.schema.json").read_text(
        encoding="utf-8"
    )
)
AUTHORITY_SCHEMA = json.loads(
    (ROOT / "shared" / "schemas" / "source-authority-result.schema.json").read_text(
        encoding="utf-8"
    )
)
DEPTH_DIVERSITY_SCHEMA = json.loads(
    (ROOT / "shared" / "schemas" / "evidence-depth-diversity-result.schema.json").read_text(
        encoding="utf-8"
    )
)


def _dimensions(**overrides: str) -> dict[str, str]:
    values = {
        "integrity": "PASS",
        "relevance": "PASS",
        "coverage": "PASS",
        "authority": "PASS",
        "diversity": "PASS",
        "depth": "PASS",
        "freshness": "PASS",
        "lineage": "PASS",
    }
    values.update(overrides)
    return values


def _claim(claim_type: str, attribute: str) -> dict[str, str]:
    return {"claim_type": claim_type, "attribute": attribute}


def _readiness(
    *,
    readiness: str,
    dimensions: dict[str, str] | None = None,
    eligible: list[str] | None = None,
    supported: list[dict[str, str]] | None = None,
    missing: list[dict[str, str]] | None = None,
    reasons: list[str] | None = None,
    evidence_count: int = 1,
) -> dict:
    return {
        "schema_version": "1.0",
        "policy_version": "v1",
        "section_index": 1,
        "section_key": "costs_and_pricing_factors",
        "readiness": readiness,
        "eligible_evidence_refs": eligible if eligible is not None else ["ev_1"],
        "supported_required_claims": supported
        if supported is not None
        else [_claim("pricing_fact", "premium")],
        "missing_required_claims": missing if missing is not None else [],
        "dimension_results": dimensions or _dimensions(),
        "reason_codes": reasons if reasons is not None else [],
        "audit": {
            "method": "evidence_quality_tests",
            "version": "v1",
            "inputs": {
                "expected_claim_map_version": "v1",
                "evidence_count": evidence_count,
            },
        },
    }


def _authority(*, state: str, source_class: str, reason_codes: list[str]) -> dict:
    return {
        "schema_version": "1.0",
        "policy_version": "v1",
        "source_id": "source_test",
        "source_class": source_class,
        "authority_state": state,
        "scope_match": "match",
        "claim_context": {
            "claim_type": "pricing_fact",
            "attribute": "premium",
        },
        "reason_codes": reason_codes,
        "audit": {"method": "evidence_quality_tests", "version": "v1"},
    }


def _depth_diversity(
    *,
    diversity_state: str,
    source_instances: list[str],
    source_families: list[str],
    independent_root_sources: list[str],
    depth_class: str = "D2",
    substantive_support: bool = True,
    reason_codes: list[str] | None = None,
) -> dict:
    return {
        "schema_version": "1.0",
        "policy_version": "v1",
        "depth": {
            "evidence_id": "ev_1",
            "depth_class": depth_class,
            "substantive_support": substantive_support,
            "claim_context": {
                "claim_type": "pricing_fact",
                "attribute": "premium",
            },
            "reason_codes": reason_codes or [],
        },
        "diversity": {
            "context": "costs_and_pricing_factors",
            "source_instances": source_instances,
            "source_families": source_families,
            "independent_root_sources": independent_root_sources,
            "state": diversity_state,
            "reason_codes": reason_codes or [],
        },
        "audit": {"method": "evidence_quality_tests", "version": "v1"},
    }


@pytest.mark.parametrize(
    "name,result",
    [
        (
            "ready_with_sufficient_evidence",
            _readiness(readiness="READY"),
        ),
        (
            "insufficient_duplicate_evidence",
            _readiness(
                readiness="INSUFFICIENT",
                dimensions=_dimensions(diversity="FAIL"),
                eligible=["ev_1", "ev_2"],
                reasons=["duplicate_source_artifact"],
                evidence_count=2,
            ),
        ),
        (
            "insufficient_weak_source",
            _readiness(
                readiness="INSUFFICIENT",
                dimensions=_dimensions(authority="FAIL"),
                reasons=["source_authority_failed"],
            ),
        ),
        (
            "insufficient_uncovered_claims",
            _readiness(
                readiness="INSUFFICIENT",
                dimensions=_dimensions(coverage="FAIL"),
                supported=[],
                missing=[_claim("pricing_factor", "cost_driver")],
                reasons=["required_claim_uncovered"],
            ),
        ),
        (
            "blocked_missing_lineage",
            _readiness(
                readiness="BLOCKED",
                dimensions=_dimensions(lineage="FAIL"),
                reasons=["lineage_missing"],
            ),
        ),
        (
            "insufficient_without_eligible_support",
            _readiness(
                readiness="INSUFFICIENT",
                dimensions=_dimensions(coverage="FAIL"),
                eligible=[],
                supported=[],
                missing=[_claim("pricing_fact", "premium")],
                reasons=["no_eligible_supporting_evidence"],
                evidence_count=0,
            ),
        ),
    ],
)
def test_readiness_vectors_match_schema(name: str, result: dict) -> None:
    Draft202012Validator(READINESS_SCHEMA).validate(result)
    assert result["audit"]["method"] == "evidence_quality_tests", name


def test_ready_vector_has_no_unexplained_gap() -> None:
    result = _readiness(readiness="READY")

    assert result["missing_required_claims"] == []
    assert result["reason_codes"] == []
    assert set(result["dimension_results"].values()) == {"PASS"}


def test_duplicate_evidence_does_not_count_as_source_diversity() -> None:
    result = _depth_diversity(
        diversity_state="FAIL",
        source_instances=["source:serp-analysis"],
        source_families=["search"],
        independent_root_sources=["root:serp-analysis"],
        reason_codes=["same_artifact_not_independent"],
    )

    Draft202012Validator(DEPTH_DIVERSITY_SCHEMA).validate(result)
    assert len(result["diversity"]["source_instances"]) == 1
    assert len(result["diversity"]["independent_root_sources"]) == 1
    assert result["diversity"]["state"] == "FAIL"


def test_weak_source_is_explicitly_failed_by_authority_policy() -> None:
    result = _authority(
        state="FAIL",
        source_class="D_community_informal",
        reason_codes=["authority_insufficient_for_claim"],
    )

    Draft202012Validator(AUTHORITY_SCHEMA).validate(result)
    assert result["authority_state"] == "FAIL"
    assert result["scope_match"] == "match"


def test_missing_claims_make_readiness_insufficient_not_ready() -> None:
    result = _readiness(
        readiness="INSUFFICIENT",
        dimensions=_dimensions(coverage="FAIL"),
        supported=[],
        missing=[
            _claim("pricing_fact", "premium"),
            _claim("pricing_factor", "cost_driver"),
        ],
        reasons=["required_claim_uncovered"],
    )

    assert result["readiness"] == "INSUFFICIENT"
    assert result["missing_required_claims"]


def test_missing_lineage_is_blocking_and_auditable() -> None:
    result = _readiness(
        readiness="BLOCKED",
        dimensions=_dimensions(lineage="FAIL"),
        reasons=["lineage_missing"],
    )

    assert result["readiness"] == "BLOCKED"
    assert result["dimension_results"]["lineage"] == "FAIL"
    assert "lineage_missing" in result["reason_codes"]


def test_readiness_contract_has_no_composite_score() -> None:
    result = _readiness(readiness="READY")

    assert "score" not in result
    assert "quality_score" not in result
    assert "authority_score" not in result
