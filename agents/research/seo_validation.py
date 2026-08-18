from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"


def _validation_id(draft_id: str, seo_strategy_id: str, payload: dict[str, Any]) -> str:
    raw = json.dumps({"draft_id": draft_id, "seo_strategy_id": seo_strategy_id, "payload": payload}, sort_keys=True, ensure_ascii=False)
    return f"seo_validation_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def validate_seo(*, article_draft: dict[str, Any], seo_strategy: dict[str, Any]) -> dict[str, Any]:
    """Deterministically validate an Article Draft against an approved SEO Strategy.

    This engine is a validator only: it does not rewrite the draft, alter the
    strategy, create evidence, or make editorial/publication decisions.
    """
    if article_draft.get("lifecycle_stage") != "draft_ready":
        raise ValueError("SEO Validation requires a draft_ready Article Draft")
    if seo_strategy.get("lifecycle_stage") != "seo_strategy_ready":
        raise ValueError("SEO Validation requires an seo_strategy_ready SEO Strategy")

    draft_ids = {k: str(article_draft.get(k, "")).strip() for k in ("draft_id", "brief_id", "report_id", "decision_id", "strategy_id")}
    strategy_ids = {k: str(seo_strategy.get(k, "")).strip() for k in ("seo_strategy_id", "brief_id", "report_id", "decision_id", "strategy_id")}
    if not all(draft_ids.values()) or not all(strategy_ids.values()):
        raise ValueError("SEO Validation requires complete lineage identifiers")
    for key in ("brief_id", "report_id", "decision_id", "strategy_id"):
        if draft_ids[key] != strategy_ids[key]:
            raise ValueError(f"SEO Validation {key} must match Article Draft and SEO Strategy")

    draft_refs = [str(x).strip() for x in article_draft.get("evidence_refs", []) if str(x).strip()]
    strategy_refs = [str(x).strip() for x in seo_strategy.get("evidence_refs", []) if str(x).strip()]
    if not draft_refs or not strategy_refs:
        raise ValueError("SEO Validation requires explicit evidence_refs on both artifacts")

    keyword = str(seo_strategy.get("primary_keyword", "")).strip().lower()
    title = str(article_draft.get("title", "")).strip().lower()
    sections = article_draft.get("sections", [])
    headings = [str(s.get("heading", "")).strip().lower() for s in sections if isinstance(s, dict)]
    required_headings = [str(x).strip().lower() for x in seo_strategy.get("heading_requirements", []) if str(x).strip()]

    checks = {
        "primary_keyword": bool(keyword) and keyword in str(article_draft.get("primary_keyword", "")).lower(),
        "title": bool(keyword) and keyword in title,
        "headings": bool(headings) and all(any(req == heading for heading in headings) for req in required_headings),
        "evidence_lineage": bool(draft_refs) and set(draft_refs).issubset(set(strategy_refs)),
        "structure": bool(sections) and all(isinstance(s, dict) and str(s.get("heading", "")).strip() and str(s.get("body", "")).strip() for s in sections),
    }

    findings: list[dict[str, str]] = []
    messages = {
        "primary_keyword": "Primary keyword is missing or inconsistent with the SEO Strategy.",
        "title": "Article title does not contain the required primary keyword.",
        "headings": "Article headings do not satisfy the SEO heading requirements.",
        "evidence_lineage": "Draft evidence_refs are not fully covered by the SEO Strategy evidence_refs.",
        "structure": "Article Draft sections are incomplete or structurally invalid.",
    }
    for category, passed in checks.items():
        if not passed:
            findings.append({"severity":"critical","category":category,"message":messages[category]})

    payload = {
        "outcome": "passed" if all(checks.values()) else "needs_revision",
        "checks": checks,
        "findings": findings,
        "evidence_refs": list(dict.fromkeys(strategy_refs)),
    }
    return {
        "seo_validation_id": _validation_id(draft_ids["draft_id"], strategy_ids["seo_strategy_id"], payload),
        "draft_id": draft_ids["draft_id"],
        "brief_id": draft_ids["brief_id"],
        "report_id": draft_ids["report_id"],
        "decision_id": draft_ids["decision_id"],
        "strategy_id": draft_ids["strategy_id"],
        "seo_strategy_id": strategy_ids["seo_strategy_id"],
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "seo_validation_ready",
        **payload,
        "audit": {"method":"article_draft_against_seo_strategy","version":METHOD_VERSION,"validation_status":"validated"},
    }
