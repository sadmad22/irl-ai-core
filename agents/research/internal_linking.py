from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlparse

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
LIFECYCLE_STAGE = "internal_linking_ready"
SOURCES = {"wordpress_api", "local_index"}
PLACEMENTS = {"intro", "body", "conclusion"}
LINK_TYPES = {"article", "guide", "comparison", "buyer_guide", "category"}


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
        raise ValueError("internal link candidate relevance_score must be between 0 and 1")
    return float(value)


def _host(value: str, field: str) -> str:
    url = _text(value, field)
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or "/" in host or " " in host:
        raise ValueError(f"{field} must be a valid hostname")
    return host


def _https_url(value: Any, field: str) -> str:
    url = _text(value, field)
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{field} must be an HTTPS URL")
    if any(char.isspace() for char in url):
        raise ValueError(f"{field} must not contain whitespace")
    return url


def _contract_id(lineage: dict[str, str], payload: dict[str, Any]) -> str:
    raw = json.dumps(
        {"lineage": lineage, "payload": payload, "schema_version": SCHEMA_VERSION, "method_version": METHOD_VERSION},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"int_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _normalize_candidate(candidate: dict[str, Any], *, site_domain: str, current_url: str | None) -> dict[str, Any]:
    allowed = {"post_id", "url", "title", "slug", "relevance_score", "source", "link_type"}
    unknown = set(candidate) - allowed
    if unknown:
        raise ValueError(f"internal link candidate contains unsupported fields: {sorted(unknown)}")
    post_id = _text(candidate.get("post_id"), "internal link candidate.post_id")
    url = _https_url(candidate.get("url"), "internal link candidate.url")
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if host != site_domain:
        raise ValueError("internal link candidate.url must belong to site_domain")
    if current_url and url.rstrip("/") == current_url.rstrip("/"):
        raise ValueError("internal link candidate.url must not target the current article")
    title = _text(candidate.get("title"), "internal link candidate.title")
    slug = _text(candidate.get("slug"), "internal link candidate.slug")
    if slug.startswith("/") or any(char.isspace() for char in slug):
        raise ValueError("internal link candidate.slug must be a relative slug without whitespace")
    source = candidate.get("source")
    if source not in SOURCES:
        raise ValueError("internal link candidate source must be wordpress_api or local_index")
    link_type = candidate.get("link_type")
    if link_type not in LINK_TYPES:
        raise ValueError(f"internal link candidate link_type must be one of {sorted(LINK_TYPES)}")
    relevance = _score(candidate.get("relevance_score"))
    return {
        "post_id": post_id,
        "url": url,
        "title": title,
        "slug": slug,
        "relevance_score": relevance,
        "source": source,
        "link_type": link_type,
    }


def build_internal_linking_contract(
    *,
    outline_editor: dict[str, Any],
    candidates: list[dict[str, Any]] | None = None,
    site_domain: str,
    current_url: str | None = None,
    enabled: bool = True,
    required: bool = False,
    max_links: int = 3,
    placement: str = "body",
    source_requirement: str = "local_index",
) -> dict[str, Any]:
    """Build a deterministic internal-link selection contract from verified site candidates.

    Discovery is upstream (WordPress API or a local index). This engine validates,
    excludes self-links, and deterministically selects candidates; it does not call
    WordPress, fetch URLs, generate anchor text, edit prose, or publish content.
    """
    if not isinstance(outline_editor, dict) or outline_editor.get("lifecycle_stage") != "outline_editor_ready":
        raise ValueError("Internal Linking requires an outline_editor_ready Outline Editor")
    lineage_fields = (
        "brief_id", "report_id", "decision_id", "strategy_id", "config_id", "outline_editor_id", "details_to_include_id"
    )
    lineage = {field: _text(outline_editor.get(field), f"Outline Editor.{field}") for field in lineage_fields}
    site_domain = _host(site_domain, "site_domain")
    if current_url is not None:
        current_url = _https_url(current_url, "current_url")
        current_host = (urlparse(current_url).hostname or "").lower().rstrip(".")
        if current_host != site_domain:
            raise ValueError("current_url must belong to site_domain")

    enabled = _bool(enabled, "enabled")
    required = _bool(required, "required")
    max_links = _int(max_links, "max_links")
    placement = _text(placement, "placement")
    source_requirement = _text(source_requirement, "source_requirement")
    if placement not in PLACEMENTS:
        raise ValueError(f"placement must be one of {sorted(PLACEMENTS)}")
    if source_requirement not in SOURCES:
        raise ValueError("source_requirement must be wordpress_api or local_index")
    if required and not enabled:
        raise ValueError("required cannot be true when disabled")
    if enabled and max_links < 1:
        raise ValueError("max_links must be at least 1 when enabled")
    if not enabled and max_links != 0:
        raise ValueError("max_links must be zero when disabled")

    normalized = [_normalize_candidate(candidate, site_domain=site_domain, current_url=current_url) for candidate in (candidates or [])]
    post_ids = [item["post_id"] for item in normalized]
    urls = [item["url"] for item in normalized]
    if len(post_ids) != len(set(post_ids)):
        raise ValueError("internal link candidate post_ids must be unique")
    if len(urls) != len(set(urls)):
        raise ValueError("internal link candidate URLs must be unique")
    if any(item["source"] != source_requirement for item in normalized):
        raise ValueError("internal link candidate source must match source_requirement")

    selected = sorted(normalized, key=lambda item: (-item["relevance_score"], item["url"]))[:max_links] if enabled else []
    if required and not selected:
        raise ValueError("required Internal Linking needs at least one verified candidate")

    payload = {
        "enabled": enabled,
        "required": required,
        "max_links": max_links,
        "placement": placement,
        "source_requirement": source_requirement,
        "site_domain": site_domain,
        "current_url": current_url,
        "links": selected,
    }
    return {
        "internal_linking_id": _contract_id(lineage, payload),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": LIFECYCLE_STAGE,
        "internal_linking": payload,
        "audit": {
            "method": "deterministic-internal-link-contract",
            "method_version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
