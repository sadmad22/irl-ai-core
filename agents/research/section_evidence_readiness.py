from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .expected_claim_map import MAP_VERSION, SCHEMA_VERSION as CLAIM_MAP_SCHEMA_VERSION, expected_claims_for
from .section_evidence_grounding import _section_key, ground_evidence_by_section

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "v1"

_DIVERSITY_REQUIRED_SECTIONS = {"how_to_compare_options"}

_ROOT = Path(__file__).resolve().parents[2]
_EVIDENCE_SCHEMA = json.loads(
    (_ROOT / "shared" / "schemas" / "evidence.schema.json").read_text(encoding="utf-8")
)
_EVIDENCE_VALIDATOR = Draft202012Validator(_EVIDENCE_SCHEMA)

_SIGNAL_CLAIMS = {
    ("query_intent", "primary_intent"),
    ("question_frequency", "count"),
    ("entity_presence", "mentioned"),
    ("entity_relevance", "score"),
    ("authority", "authority_score"),
    ("authority", "topic_fit"),
}

_AUTHORITY_CLASS_BY_SOURCE_TYPE = {
    "official": "A_primary_official",
    "government": "A_primary_official",
    "regulator": "A_primary_official",
    "government_agency": "A_primary_official",
    "policy_document": "A_primary_official",
    "institutional": "B_institutional_professional",
    "professional": "B_institutional_professional",
    "association": "B_institutional_professional",
    "secondary": "C_reputable_secondary",
    "publisher": "C_reputable_secondary",
    "research_report": "C_reputable_secondary",
    "news": "C_reputable_secondary",
    "community": "D_community_informal",
    "forum": "D_community_informal",
    "user_generated": "D_community_informal",
    "query": "E_discovery_search_surface",
    "serp": "E_discovery_search_surface",
    "search_result": "E_discovery_search_surface",
    "search_surface": "E_discovery_search_surface",
}


def _claim_ref(record: dict[str, Any]) -> tuple[str, str]:
    claim = record.get("claim") if isinstance(record.get("claim"), dict) else {}
    return str(claim.get("type", "")).strip(), str(claim.get("attribute", "")).strip()


def _source(record: dict[str, Any]) -> dict[str, Any]:
    source = record.get("source")
    return source if isinstance(source, dict) else {}


def _is_nonempty_value(record: dict[str, Any]) -> bool:
    value = record.get("value") if isinstance(record.get("value"), dict) else {}
    if "data" not in value:
        return False
    data = value.get("data")
    if data is None:
        return False
    if isinstance(data, str) and not data.strip():
        return False
    if isinstance(data, (list, dict)) and not data:
        return False
    return True


def _depth_class(record: dict[str, Any], *, required_claim: tuple[str, str] | None = None) -> tuple[str, bool, list[str]]:
    claim_type, attribute = _claim_ref(record)
    if (claim_type, attribute) in _SIGNAL_CLAIMS:
        return "D0", False, ["surface_signal"]

    if not claim_type or not attribute:
        return "D0", False, ["depth_unknown"]

    subject = record.get("subject") if isinstance(record.get("subject"), dict) else {}
    has_scope = bool(str(subject.get("type", "")).strip() and str(subject.get("id", "")).strip())
    if not has_scope or not _is_nonempty_value(record):
        return "D1", False, ["scope_incomplete" if not has_scope else "value_non_substantive"]

    if required_claim is not None and (claim_type, attribute) != required_claim:
        return "D1", False, ["contextual_only"]

    return "D2", True, ["substantive_support"]


def _authority_state(record: dict[str, Any], required: bool) -> str:
    if not required:
        return "PASS"
    source_type = str(_source(record).get("type", "")).strip().lower()
    source_class = _AUTHORITY_CLASS_BY_SOURCE_TYPE.get(source_type)
    if source_class in {"A_primary_official", "B_institutional_professional", "C_reputable_secondary"}:
        return "PASS"
    if source_class in {"D_community_informal", "E_discovery_search_surface"}:
        return "FAIL"
    return "UNKNOWN"


def _root_identity(record: dict[str, Any]) -> str | None:
    source = _source(record)
    for key in ("source_id", "url", "document_id", "artifact"):
        value = str(source.get(key, "")).strip()
        if value:
            return value
    roots = record.get("derived_from")
    if isinstance(roots, list) and roots:
        normalized = sorted(str(item).strip() for item in roots if str(item).strip())
        if normalized:
            return "derived:" + "|".join(normalized)
    return None


def _freshness_state(records: list[dict[str, Any]]) -> str:
    if not records:
        return "UNKNOWN"
    for record in records:
        if not str(record.get("captured_at", "")).strip():
            return "UNKNOWN"
        if _source(record).get("retrieved_at") in (None, ""):
            return "UNKNOWN"
    return "PASS"


def _lineage_state(record: dict[str, Any]) -> str:
    evidence_type = str(record.get("type", "")).strip()
    derived_from = record.get("derived_from")
    if not isinstance(derived_from, list):
        return "FAIL"
    if evidence_type == "derived" and not derived_from:
        return "FAIL"
    if evidence_type != "derived" and any(not str(item).strip() for item in derived_from):
        return "FAIL"
    return "PASS"


def _dedupe_claims(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for item in items:
        key = (item["claim_type"], item["attribute"])
        if key not in seen:
            result.append({"claim_type": key[0], "attribute": key[1]})
            seen.add(key)
    return result


def _result(
    *,
    section_index: int,
    section_key: str,
    readiness: str,
    eligible_refs: list[str],
    supported: list[dict[str, str]],
    missing: list[dict[str, str]],
    dimensions: dict[str, str],
    reasons: list[str],
    evidence_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "section_index": section_index,
        "section_key": section_key,
        "readiness": readiness,
        "eligible_evidence_refs": list(dict.fromkeys(eligible_refs)),
        "supported_required_claims": _dedupe_claims(supported),
        "missing_required_claims": _dedupe_claims(missing),
        "dimension_results": dimensions,
        "reason_codes": list(dict.fromkeys(reasons)),
        "audit": {
            "method": "section_evidence_readiness_gate",
            "version": "v1",
            "inputs": {
                "expected_claim_map_version": MAP_VERSION,
                "evidence_count": evidence_count,
            },
        },
    }


def _claim_list(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result = []
    for item in items:
        value = (item["claim_type"], item["attribute"])
        if value not in seen:
            result.append(item)
            seen.add(value)
    return result


def evaluate_section_readiness(
    *,
    outline: list[dict[str, Any]],
    evidence_refs: list[str],
    evidence_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(outline, list) or not outline:
        raise ValueError("Section readiness requires a non-empty outline")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        raise ValueError("Section readiness requires explicit evidence_refs")

    normalized_refs = list(dict.fromkeys(str(ref).strip() for ref in evidence_refs if str(ref).strip()))
    indexed = {
        str(record.get("evidence_id", "")).strip(): record
        for record in evidence_records
        if isinstance(record, dict) and str(record.get("evidence_id", "")).strip()
    }
    eligible_by_section = ground_evidence_by_section(
        outline=outline,
        evidence_refs=normalized_refs,
        evidence_records=evidence_records,
        per_section=max(1, len(indexed)),
    )

    results: list[dict[str, Any]] = []
    for section_number, (section, eligible_refs) in enumerate(zip(outline, eligible_by_section), start=1):
        key = _section_key(section)
        claim_map = expected_claims_for(key)
        if claim_map is None or CLAIM_MAP_SCHEMA_VERSION != "1.0":
            results.append(
                _result(
                    section_index=section_number,
                    section_key=key,
                    readiness="BLOCKED",
                    eligible_refs=eligible_refs,
                    supported=[],
                    missing=[],
                    dimensions={
                        "integrity": "UNKNOWN",
                        "relevance": "UNKNOWN",
                        "coverage": "UNKNOWN",
                        "authority": "UNKNOWN",
                        "diversity": "UNKNOWN",
                        "depth": "UNKNOWN",
                        "freshness": "UNKNOWN",
                        "lineage": "UNKNOWN",
                    },
                    reasons=["context_missing"],
                    evidence_count=len(eligible_refs),
                )
            )
            continue

        eligible_records = [indexed[ref] for ref in eligible_refs if ref in indexed]
        required_families = {
            (item["claim_type"], item["attribute"])
            for item in claim_map["required_claims"]
        }
        invalid_records = []
        for record in eligible_records:
            if _claim_ref(record) not in required_families:
                continue
            if not list(_EVIDENCE_VALIDATOR.iter_errors(record)):
                continue
            invalid_records.append(record)

        if invalid_records:
            results.append(
                _result(
                    section_index=section_number,
                    section_key=key,
                    readiness="BLOCKED",
                    eligible_refs=eligible_refs,
                    supported=[],
                    missing=[{"claim_type": item["claim_type"], "attribute": item["attribute"]} for item in claim_map["required_claims"]],
                    dimensions={
                        "integrity": "FAIL",
                        "relevance": "PASS" if eligible_refs else "FAIL",
                        "coverage": "UNKNOWN",
                        "authority": "UNKNOWN",
                        "diversity": "UNKNOWN",
                        "depth": "UNKNOWN",
                        "freshness": "UNKNOWN",
                        "lineage": "FAIL",
                    },
                    reasons=["evidence_contract_invalid"],
                    evidence_count=len(eligible_refs),
                )
            )
            continue

        if not eligible_records:
            results.append(
                _result(
                    section_index=section_number,
                    section_key=key,
                    readiness="INSUFFICIENT",
                    eligible_refs=[],
                    supported=[],
                    missing=[{"claim_type": item["claim_type"], "attribute": item["attribute"]} for item in claim_map["required_claims"]],
                    dimensions={
                        "integrity": "PASS",
                        "relevance": "FAIL",
                        "coverage": "FAIL",
                        "authority": "UNKNOWN",
                        "diversity": "UNKNOWN",
                        "depth": "UNKNOWN",
                        "freshness": "UNKNOWN",
                        "lineage": "PASS",
                    },
                    reasons=["no_eligible_supporting_evidence"],
                    evidence_count=0,
                )
            )
            continue

        supporting: dict[tuple[str, str], list[dict[str, Any]]] = {}
        claim_policies: dict[tuple[str, str], str] = {}
        for required_claim in claim_map["required_claims"]:
            family = (required_claim["claim_type"], required_claim["attribute"])
            claim_policies[family] = str(required_claim["evidence_kind"])
            matches = []
            for record in eligible_records:
                if _claim_ref(record) != family:
                    continue
                depth_class, substantive, _ = _depth_class(
                    record,
                    required_claim=family if required_claim["evidence_kind"] == "substantive" else None,
                )
                if required_claim["evidence_kind"] == "signal":
                    if depth_class == "D0":
                        matches.append(record)
                elif depth_class == "D2" and substantive:
                    matches.append(record)
            if matches:
                supporting[family] = matches

        required_claims = [
            {"claim_type": item["claim_type"], "attribute": item["attribute"]}
            for item in claim_map["required_claims"]
        ]
        supported = [claim for claim in required_claims if (claim["claim_type"], claim["attribute"]) in supporting]
        missing = [claim for claim in required_claims if (claim["claim_type"], claim["attribute"]) not in supporting]

        integrity = "PASS"
        relevance = "PASS"
        coverage = "PASS" if not missing else "FAIL"

        used_records = [
            record
            for family, records in supporting.items()
            for record in records
            if claim_policies.get(family) == "substantive"
        ]
        authority_states = [_authority_state(record, True) for record in used_records]
        authority = "FAIL" if "FAIL" in authority_states else ("UNKNOWN" if "UNKNOWN" in authority_states else "PASS")


        root_ids = [root for record in used_records if (root := _root_identity(record))]
        unique_roots = set(root_ids)
        if key not in _DIVERSITY_REQUIRED_SECTIONS:
            diversity = "PASS"
            diversity_reason = "diversity_not_required"
        elif len(root_ids) > 1 and len(unique_roots) == 1:
            diversity = "FAIL"
            diversity_reason = "same_source_origin"
        elif len(root_ids) == 0:
            diversity = "UNKNOWN"
            diversity_reason = "independence_unknown"
        elif len(unique_roots) < 2:
            diversity = "FAIL"
            diversity_reason = "diversity_insufficient"
        else:
            diversity = "PASS"
            diversity_reason = "independent_source"

        if not used_records:
            depth = "UNKNOWN"
        else:
            depth = "PASS" if all(
                _depth_class(record, required_claim=_claim_ref(record))[1]
                for record in used_records
            ) else "FAIL"

        freshness = _freshness_state(used_records)
        lineage_states = [_lineage_state(record) for record in used_records]
        lineage = "FAIL" if "FAIL" in lineage_states else "PASS"

        hard_block = integrity == "FAIL" or lineage == "FAIL"
        reasons: list[str] = []
        if missing:
            reasons.append("required_claim_missing")
        if authority == "FAIL":
            reasons.append("authority_insufficient")
        elif authority == "UNKNOWN":
            reasons.append("dimension_unknown")
        if diversity == "FAIL":
            reasons.append(diversity_reason)
            reasons.append("diversity_insufficient")
        elif diversity == "UNKNOWN":
            reasons.append(diversity_reason)
            reasons.append("dimension_unknown")
        if depth == "FAIL":
            reasons.append("depth_insufficient")
        elif depth == "UNKNOWN" and used_records:
            reasons.append("dimension_unknown")
        if freshness == "UNKNOWN":
            reasons.append("dimension_unknown")
        if lineage == "FAIL":
            reasons.append("lineage_invalid")

        readiness = "BLOCKED" if hard_block else ("INSUFFICIENT" if reasons else "READY")
        results.append(
            _result(
                section_index=section_number,
                section_key=key,
                readiness=readiness,
                eligible_refs=eligible_refs,
                supported=_claim_list(supported),
                missing=_claim_list(missing),
                dimensions={
                    "integrity": integrity,
                    "relevance": relevance,
                    "coverage": coverage,
                    "authority": authority,
                    "diversity": diversity,
                    "depth": depth,
                    "freshness": freshness,
                    "lineage": lineage,
                },
                reasons=reasons,
                evidence_count=len(eligible_refs),
            )
        )

    return results


def require_ready_sections(
    *,
    outline: list[dict[str, Any]],
    evidence_refs: list[str],
    evidence_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results = evaluate_section_readiness(
        outline=outline,
        evidence_refs=evidence_refs,
        evidence_records=evidence_records,
    )
    failures = [item for item in results if item["readiness"] != "READY"]
    if failures:
        details = "; ".join(
            f"section {item['section_index']} {item['section_key']}: "
            f"{item['readiness']} ({', '.join(item['reason_codes']) or 'no_reason'})"
            for item in failures
        )
        raise ValueError(f"Section Evidence Quality Gate blocked Article Writer: {details}")
    return results
