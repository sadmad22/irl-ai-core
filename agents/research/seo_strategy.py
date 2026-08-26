from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"


def _id(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return "seo_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_seo_strategy(
    *,
    content_brief: dict[str, Any],
    research_report: dict[str, Any],
    article_draft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if content_brief.get("lifecycle_stage") != "content_brief_ready":
        raise ValueError("SEO Strategy requires a content_brief_ready Content Brief")

    ids = {k: str(content_brief.get(k, "")).strip() for k in ("brief_id", "report_id", "decision_id", "strategy_id")}
    if not all(ids.values()):
        raise ValueError("Content Brief lineage identifiers are required")
    if str(research_report.get("report_id", "")).strip() != ids["report_id"]:
        raise ValueError("SEO Strategy report_id must match ResearchReport")

    primary = str(content_brief.get("primary_keyword", "")).strip()
    intent = str(content_brief.get("search_intent", "")).strip()
    if not primary or not intent:
        raise ValueError("Content Brief primary_keyword and search_intent are required")

    refs = [str(x) for x in content_brief.get("evidence_refs", []) if str(x).strip()]
    if not refs:
        raise ValueError("SEO Strategy requires explicit evidence_refs")

    if article_draft is not None:
        draft_refs = [
            str(x)
            for x in article_draft.get("evidence_refs", [])
            if str(x).strip()
        ]
        refs.extend(draft_refs)

    refs = list(dict.fromkeys(refs))

    entity_analysis = research_report.get("entity_analysis", {}) or {}
    question_analysis = research_report.get("question_analysis", {}) or {}
    entities = entity_analysis.get("entities", []) or []
    questions = question_analysis.get("questions", []) or []

    topical_entities = []
    for item in entities:
        value = item.get("entity") if isinstance(item, dict) else item
        if str(value).strip():
            topical_entities.append(str(value).strip())
    topical_entities = list(dict.fromkeys(topical_entities))

    questions_to_answer = []
    for item in questions:
        value = item.get("question") if isinstance(item, dict) else item
        if str(value).strip():
            questions_to_answer.append(str(value).strip())
    questions_to_answer = list(dict.fromkeys(questions_to_answer))

    sections = content_brief.get("outline", []) or []
    heading_requirements = [
        str(s.get("heading")).strip() for s in sections
        if isinstance(s, dict) and str(s.get("heading", "")).strip()
    ]

    payload = {
        "brief_id": ids["brief_id"], "report_id": ids["report_id"], "decision_id": ids["decision_id"], "strategy_id": ids["strategy_id"],
        "primary_keyword": primary, "secondary_keywords": [], "search_intent": intent,
        "title_requirements": [f"Align title with the primary keyword: {primary}", "Match the confirmed search intent."],
        "meta_description_requirements": ["Summarize the page accurately", f"Reflect the primary topic: {primary}"],
        "heading_requirements": heading_requirements or ["Use descriptive headings aligned with the approved brief outline."],
        "topical_entities": topical_entities, "questions_to_answer": questions_to_answer,
        "internal_link_targets": list(content_brief.get("internal_link_targets", []) or []),
        "schema_requirements": ["Use only structured data supported by the final published content."],
        "image_alt_requirements": ["Describe informative images accurately and concisely; do not keyword-stuff alt text."],
        "evidence_refs": list(dict.fromkeys(refs)),
    }
    return {
        "seo_strategy_id": _id(payload), **payload,
        "schema_version": SCHEMA_VERSION, "lifecycle_stage": "seo_strategy_ready",
        "audit": {"method":"research_grounded_seo_strategy","version":METHOD_VERSION,"validation_status":"validated"},
    }
