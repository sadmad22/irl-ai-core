from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"


def _draft_id(brief: dict[str, Any], payload: dict[str, Any]) -> str:
    raw = json.dumps(
        {"brief_id": brief["brief_id"], "payload": payload},
        sort_keys=True,
        ensure_ascii=False,
    )
    return f"draft_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _title(brief: dict[str, Any]) -> str:
    keyword = brief["primary_keyword"]
    content_type = brief["content_type"]
    prefixes = {
        "guide": "A Practical Guide to",
        "comparison": "Comparing",
        "buyer_guide": "How to Choose",
        "article": "Understanding",
    }
    return f"{prefixes[content_type]} {keyword.title()}"


def _section_body(section: dict[str, str]) -> str:
    # This v1 writer produces a controlled, reviewable draft scaffold rather
    # than inventing factual claims. Claim generation belongs to a later
    # evidence-grounded writing implementation.
    return (
        f"Draft this section to {section['purpose']} "
        "Use the upstream evidence_refs for factual claims and mark any claim "
        "that still requires editorial verification before publication."
    )


def build_article_draft(*, content_brief: dict[str, Any]) -> dict[str, Any]:
    """Translate an approved Content Brief into a deterministic draft scaffold.

    The Writer layer consumes the brief. It does not make decisions, change
    strategy, create evidence, or claim that unverified facts are publishable.
    """
    brief_id = str(content_brief.get("brief_id", "")).strip()
    report_id = str(content_brief.get("report_id", "")).strip()
    decision_id = str(content_brief.get("decision_id", "")).strip()
    strategy_id = str(content_brief.get("strategy_id", "")).strip()
    if not all((brief_id, report_id, decision_id, strategy_id)):
        raise ValueError("Content Brief lineage identifiers are required")
    if content_brief.get("lifecycle_stage") != "content_brief_ready":
        raise ValueError("Article Draft requires a content_brief_ready Content Brief")

    refs = content_brief.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        raise ValueError("Content Brief must contain explicit evidence_refs")

    outline = content_brief.get("outline")
    if not isinstance(outline, list) or not outline:
        raise ValueError("Content Brief must contain a non-empty outline")

    content_type = content_brief.get("content_type")
    keyword = str(content_brief.get("primary_keyword", "")).strip()
    if content_type not in {"guide", "comparison", "buyer_guide", "article"}:
        raise ValueError("Content Brief.content_type is invalid")
    if not keyword:
        raise ValueError("Content Brief.primary_keyword is required")

    sections = [
        {
            "heading": str(item["heading"]).strip(),
            "purpose": str(item["purpose"]).strip(),
            "body": _section_body(item),
        }
        for item in outline
    ]

    payload = {
        "title": _title(content_brief),
        "content_type": content_type,
        "primary_keyword": keyword,
        "sections": sections,
        "evidence_refs": list(dict.fromkeys(str(ref) for ref in refs if str(ref).strip())),
        "editorial_constraints": list(dict.fromkeys(
            str(value) for value in content_brief.get("editorial_constraints", []) if str(value).strip()
        )),
    }

    return {
        "draft_id": _draft_id(content_brief, payload),
        "brief_id": brief_id,
        "report_id": report_id,
        "decision_id": decision_id,
        "strategy_id": strategy_id,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "draft_ready",
        **payload,
        "audit": {
            "method": "content_brief_to_article_draft",
            "version": METHOD_VERSION,
            "validation_status": "pending",
        },
    }
