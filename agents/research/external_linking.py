from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
LIFECYCLE_STAGE = "external_linking_ready"
SOURCES = {"dataforseo", "search"}
PLACEMENTS = {"intro", "body", "conclusion"}
LINK_TYPES = {"official", "research", "reference", "guidance"}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value


def _int(value: Any, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")
    return value


def _score(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError("external link candidate relevance_score must be between 0 and 1")
    return float(value)


def _contract_id(lineage: dict[str, str], payload: dict[str, Any]) -> str:
    raw = json.dumps({"lineage": lineage, "payload": payload, "schema_version": SCHEMA_VERSION, "method_version": METHOD_VERSION}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"ext_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    allowed = {"url", "title", "domain", "relevance_score", "source", "link_type"}
    unknown = set(candidate) - allowed
    if unknown:
        raise ValueError(f"external link candidate contains unsupported fields: {sorted(unknown)}")
    source = candidate.get("source")
    if source not in SOURCES:
        raise ValueError("external link candidate source must be dataforseo or search")
    link_type = candidate.get("link_type")
    if link_type not in LINK_TYPES:
        raise ValueError(f"external link candidate link_type must be one of {sorted(LINK_TYPES)}")
    url = _text(candidate.get("url"), "external link candidate.url")
    if not url.startswith("https://"):
        raise ValueError("external link candidate.url must use HTTPS")
    if any(char.isspace() for char in url):
        raise ValueError("external link candidate.url must not contain whitespace")
    title = _text(candidate.get("title"), "external link candidate.title")
    domain = _text(candidate.get("domain"), "external link candidate.domain").lower()
    if "/" in domain or " " in domain:
        raise ValueError("external link candidate.domain must be a hostname")
    relevance = _score(candidate.get("relevance_score"))
    return {"url": url, "title": title, "domain": domain, "relevance_score": relevance, "source": source, "link_type": link_type}


def build_external_linking_contract(*, outline_editor: dict[str, Any], candidates: list[dict[str, Any]] | None = None, enabled: bool = True, required: bool = False, max_links: int = 3, placement: str = "body", source_requirement: str = "search") -> dict[str, Any]:
    """Build a deterministic external-link selection contract from verified search candidates.

    The engine does not fetch URLs, call DataForSEO/Search, generate anchor text, or
    insert links into article prose. Discovery and verification happen upstream;
    rendering remains downstream.
    """
    if not isinstance(outline_editor, dict) or outline_editor.get("lifecycle_stage") != "outline_editor_ready":
        raise ValueError("External Linking requires an outline_editor_ready Outline Editor")
    lineage_fields = ("brief_id", "report_id", "decision_id", "strategy_id", "config_id", "outline_editor_id", "details_to_include_id")
    lineage = {field: _text(outline_editor.get(field), f"Outline Editor.{field}") for field in lineage_fields}
    enabled = _bool(enabled, "enabled")
    required = _bool(required, "required")
    max_links = _int(max_links, "max_links")
    placement = _text(placement, "placement")
    source_requirement = _text(source_requirement, "source_requirement")
    if placement not in PLACEMENTS:
        raise ValueError(f"placement must be one of {sorted(PLACEMENTS)}")
    if source_requirement not in SOURCES:
        raise ValueError("source_requirement must be dataforseo or search")
    if required and not enabled:
        raise ValueError("required cannot be true when disabled")
    if enabled and max_links < 1:
        raise ValueError("max_links must be at least 1 when enabled")
    if not enabled and max_links != 0:
        raise ValueError("max_links must be zero when disabled")

    normalized = [_normalize_candidate(candidate) for candidate in (candidates or [])]
    urls = [item["url"] for item in normalized]
    if len(urls) != len(set(urls)):
        raise ValueError("external link candidate URLs must be unique")
    if any(item["source"] != source_requirement for item in normalized):
        raise ValueError("external link candidate source must match source_requirement")
    selected = sorted(normalized, key=lambda item: (-item["relevance_score"], item["url"]))[:max_links] if enabled else []
    if required and not selected:
        raise ValueError("required External Linking needs at least one verified candidate")

    payload = {"enabled": enabled, "required": required, "max_links": max_links, "placement": placement, "source_requirement": source_requirement, "links": selected}
    return {
        "external_linking_id": _contract_id(lineage, payload),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": LIFECYCLE_STAGE,
        "external_linking": payload,
        "audit": {"method": "deterministic-external-link-contract", "method_version": METHOD_VERSION, "validation_status": "validated"},
    }
