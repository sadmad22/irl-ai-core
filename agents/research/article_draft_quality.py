from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v4"
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "shared" / "schemas" / "article-draft.schema.json"
_PLACEHOLDER_PATTERNS = ("draft this section", "use the upstream evidence_refs", "mark any claim", "without introducing unsupported claims", "requirement from the approved content strategy")
_METADATA_LEAKAGE_PATTERNS = ("the research evidence records", "evidence_id", "subject_id", "claim.attribute", "raw evidence")
_FORBIDDEN_TOP_LEVEL_KEYS = {"decision", "recommendation", "decision_result", "recommendation_result"}
_CLAIM_ID_PATTERN = re.compile(r"^claim_(\d+)_(\d+)_([a-z0-9]+)$")


def _quality_id(draft_id: str, payload: dict[str, Any]) -> str:
    raw = json.dumps({"draft_id": draft_id, "payload": payload}, sort_keys=True, ensure_ascii=False)
    return f"article_draft_quality_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _schema_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(_SCHEMA_PATH.read_text(encoding="utf-8")))


def _schema_check(article_draft: dict[str, Any]) -> tuple[bool, str | None]:
    errors = sorted(_schema_validator().iter_errors(article_draft), key=lambda error: list(error.path))
    if not errors: return True, None
    error = errors[0]; location = ".".join(str(part) for part in error.path) or "root"
    return False, f"Article Draft contract violation at {location}: {error.message}"


def _lineage_check(article_draft: dict[str, Any]) -> bool:
    return all(str(article_draft.get(key, "")).strip() for key in ("draft_id", "brief_id", "report_id", "decision_id", "strategy_id"))


def _structure_check(article_draft: dict[str, Any]) -> bool:
    sections = article_draft.get("sections", [])
    if not isinstance(sections, list) or not sections: return False
    return bool(str(article_draft.get("title", "")).strip()) and bool(str(article_draft.get("primary_keyword", "")).strip()) and all(isinstance(section, dict) and all(str(section.get(key, "")).strip() for key in ("heading", "purpose", "body")) for section in sections)


def _evidence_check(article_draft: dict[str, Any]) -> bool:
    refs = article_draft.get("evidence_refs")
    return isinstance(refs, list) and bool(refs) and len(refs) == len(set(str(ref).strip() for ref in refs)) and all(str(ref).strip() for ref in refs)


def _section_evidence_check(article_draft: dict[str, Any]) -> tuple[bool, list[str]]:
    top_refs = {str(ref).strip() for ref in article_draft.get("evidence_refs", []) if str(ref).strip()}; errors: list[str] = []
    for index, section in enumerate(article_draft.get("sections", []), start=1):
        if not isinstance(section, dict): errors.append(f"section_{index}:not_an_object"); continue
        refs = section.get("evidence_refs"); normalized = [str(ref).strip() for ref in refs] if isinstance(refs, list) else []
        if not normalized: errors.append(f"section_{index}:missing_evidence_refs"); continue
        if len(normalized) != len(set(normalized)): errors.append(f"section_{index}:duplicate_evidence_refs")
        if any(ref not in top_refs for ref in normalized): errors.append(f"section_{index}:evidence_ref_not_in_top_level_lineage")
        if not str(section.get("body", "")).strip(): errors.append(f"section_{index}:empty_body")
    return not errors, errors


def _claim_evidence_check(article_draft: dict[str, Any]) -> tuple[bool, list[str]]:
    top_refs = {str(ref).strip() for ref in article_draft.get("evidence_refs", []) if str(ref).strip()}; errors: list[str] = []; global_claim_ids: set[str] = set()
    for section_index, section in enumerate(article_draft.get("sections", []), start=1):
        section_refs = {str(ref).strip() for ref in section.get("evidence_refs", []) if str(ref).strip()}; claims = section.get("claims")
        if not isinstance(claims, list) or not claims: errors.append(f"section_{section_index}:missing_claims"); continue
        for claim_index, claim in enumerate(claims, start=1):
            if not isinstance(claim, dict): errors.append(f"section_{section_index}:claim_{claim_index}:not_an_object"); continue
            claim_id = str(claim.get("claim_id", "")).strip(); text = str(claim.get("text", "")).strip(); refs = [str(ref).strip() for ref in claim.get("evidence_refs", [])] if isinstance(claim.get("evidence_refs"), list) else []; status = str(claim.get("grounding_status", "")).strip()
            if not claim_id: errors.append(f"section_{section_index}:claim_{claim_index}:missing_claim_id")
            else:
                if claim_id in global_claim_ids: errors.append(f"section_{section_index}:claim_{claim_index}:duplicate_claim_id")
                global_claim_ids.add(claim_id); match = _CLAIM_ID_PATTERN.fullmatch(claim_id)
                if not match: errors.append(f"section_{section_index}:claim_{claim_index}:invalid_claim_id_format")
                elif int(match.group(1)) != section_index or int(match.group(2)) != claim_index: errors.append(f"section_{section_index}:claim_{claim_index}:claim_id_lineage_mismatch")
            if not text: errors.append(f"section_{section_index}:claim_{claim_index}:empty_text")
            if len(refs) != len(set(refs)): errors.append(f"section_{section_index}:claim_{claim_index}:duplicate_evidence_refs")
            if any(not ref for ref in refs): errors.append(f"section_{section_index}:claim_{claim_index}:empty_evidence_ref")
            if any(ref not in section_refs or ref not in top_refs for ref in refs): errors.append(f"section_{section_index}:claim_{claim_index}:evidence_ref_outside_lineage")
            if status == "grounded" and not refs: errors.append(f"section_{section_index}:claim_{claim_index}:grounded_without_evidence")
            elif status == "blocked": errors.append(f"section_{section_index}:claim_{claim_index}:not_grounded")
            elif status == "provisional": errors.append(f"section_{section_index}:claim_{claim_index}:provisional_not_publishable")
            elif status != "grounded": errors.append(f"section_{section_index}:claim_{claim_index}:invalid_grounding_status")
    return not errors, errors


def _placeholder_check(article_draft: dict[str, Any]) -> tuple[bool, list[str]]:
    hits = [f"section_{index}:{pattern}" for index, section in enumerate(article_draft.get("sections", []), start=1) if isinstance(section, dict) for pattern in _PLACEHOLDER_PATTERNS if pattern in str(section.get("body", "")).strip().lower()]
    return not hits, hits


def _metadata_leakage_check(article_draft: dict[str, Any]) -> tuple[bool, list[str]]:
    hits = [f"section_{index}:{pattern}" for index, section in enumerate(article_draft.get("sections", []), start=1) if isinstance(section, dict) for pattern in _METADATA_LEAKAGE_PATTERNS if pattern in str(section.get("body", "")).lower()]
    return not hits, hits


def _assets_check(article_draft: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    sections = article_draft.get("sections", []); section_count = len(sections) if isinstance(sections, list) else 0
    images = article_draft.get("images")
    if not isinstance(images, list) or not images: errors.append("images:missing")
    else:
        ids: set[str] = set()
        for image in images:
            if not isinstance(image, dict): errors.append("images:not_an_object"); continue
            image_id = str(image.get("image_id", "")).strip(); index = image.get("section_index")
            if not image_id or image_id in ids: errors.append("images:duplicate_or_empty_id")
            ids.add(image_id)
            if isinstance(index, bool) or not isinstance(index, int) or index < 0 or index >= section_count: errors.append("images:invalid_section_index")
            if not str(image.get("prompt", "")).strip() or not str(image.get("alt_text", "")).strip(): errors.append("images:missing_prompt_or_alt_text")
            if "url" in image or "src" in image or "media_id" in image: errors.append("images:fake_or_unresolved_media_reference")
    tables = article_draft.get("tables", [])
    if not isinstance(tables, list): errors.append("tables:not_an_array")
    if article_draft.get("content_type") in {"comparison", "buyer_guide"} and not tables: errors.append("tables:required_for_content_type")
    return not errors, errors


def _decision_engine_check(article_draft: dict[str, Any]) -> tuple[bool, list[str]]:
    leaked = sorted(_FORBIDDEN_TOP_LEVEL_KEYS.intersection(article_draft.keys()))
    return not leaked, leaked


def validate_article_draft_quality(*, article_draft: dict[str, Any]) -> dict[str, Any]:
    """Validate Article Draft contract, writer prose, assets, grounding, and publishability."""
    if article_draft.get("lifecycle_stage") != "draft_ready": raise ValueError("Article Draft Quality requires a draft_ready Article Draft")
    draft_id = str(article_draft.get("draft_id", "")).strip()
    if not draft_id: raise ValueError("Article Draft Quality requires draft_id")
    lineage_ok = _lineage_check(article_draft); contract_ok, contract_message = _schema_check(article_draft); structure_ok = _structure_check(article_draft); evidence_ok = _evidence_check(article_draft); section_evidence_ok, section_evidence_errors = _section_evidence_check(article_draft); claim_evidence_ok, claim_evidence_errors = _claim_evidence_check(article_draft); placeholders_ok, placeholder_hits = _placeholder_check(article_draft); metadata_ok, metadata_hits = _metadata_leakage_check(article_draft); assets_ok, asset_errors = _assets_check(article_draft); decision_ok, leaked_keys = _decision_engine_check(article_draft)
    checks = {"contract": contract_ok, "lineage": lineage_ok, "structure": structure_ok, "evidence_lineage": evidence_ok, "section_evidence_grounding": section_evidence_ok, "claim_evidence_grounding": claim_evidence_ok, "placeholders": placeholders_ok, "metadata_leakage": metadata_ok, "structured_assets": assets_ok, "decision_engine_leakage": decision_ok}
    findings: list[dict[str, str]] = []
    if not contract_ok: findings.append({"severity": "critical", "category": "contract", "message": contract_message or "Article Draft does not satisfy its schema contract."})
    if not lineage_ok: findings.append({"severity": "critical", "category": "lineage", "message": "Article Draft lineage identifiers are incomplete."})
    if not structure_ok: findings.append({"severity": "critical", "category": "structure", "message": "Article Draft title, primary keyword, or section structure is incomplete."})
    if not evidence_ok: findings.append({"severity": "critical", "category": "evidence_lineage", "message": "Article Draft requires a non-empty, unique evidence_refs list."})
    if not section_evidence_ok: findings.append({"severity": "critical", "category": "section_evidence_grounding", "message": "Invalid section evidence grounding: " + ", ".join(section_evidence_errors)})
    if not claim_evidence_ok: findings.append({"severity": "critical", "category": "claim_evidence_grounding", "message": "Invalid claim evidence grounding: " + ", ".join(claim_evidence_errors)})
    if not placeholders_ok: findings.append({"severity": "critical", "category": "placeholders", "message": "Article Draft contains unresolved generation placeholders: " + ", ".join(placeholder_hits)})
    if not metadata_ok: findings.append({"severity": "critical", "category": "metadata_leakage", "message": "Article Draft prose contains internal research metadata: " + ", ".join(metadata_hits)})
    if not assets_ok: findings.append({"severity": "critical", "category": "structured_assets", "message": "Article Draft structured assets are invalid: " + ", ".join(asset_errors)})
    if not decision_ok: findings.append({"severity": "critical", "category": "decision_engine_leakage", "message": "Article Draft contains forbidden decision/recommendation fields: " + ", ".join(leaked_keys)})
    evidence_refs = list(dict.fromkeys(str(ref).strip() for ref in article_draft.get("evidence_refs", []) if str(ref).strip()))
    payload = {"outcome": "passed" if all(checks.values()) else "needs_revision", "checks": checks, "findings": findings, "evidence_refs": evidence_refs}
    return {"quality_id": _quality_id(draft_id, payload), "draft_id": draft_id, "brief_id": str(article_draft.get("brief_id", "")).strip(), "report_id": str(article_draft.get("report_id", "")).strip(), "decision_id": str(article_draft.get("decision_id", "")).strip(), "strategy_id": str(article_draft.get("strategy_id", "")).strip(), "schema_version": SCHEMA_VERSION, "lifecycle_stage": "article_draft_quality_ready", **payload, "audit": {"method": "article_draft_quality_validator", "version": METHOD_VERSION, "validation_status": "validated"}}
