from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
LIFECYCLE_STAGE = "content_optimization_ready"

CATEGORIES = {"keyword", "semantic", "topic", "heading", "coverage", "entity", "question"}
SOURCES = {"semantic_seo", "outline_editor", "details_to_include", "dataforseo"}
MODES = {"coverage", "competitive", "combined"}
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _normalized_phrase(text: str) -> str:
    return " ".join(token.casefold() for token in TOKEN_RE.findall(text))


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in TOKEN_RE.findall(text)}


def _coverage(target: str, article_text: str) -> float:
    """Return coverage for a target phrase.

    v1 treats a target as covered only when its normalized phrase occurs in the
    article. Partial token overlap is not sufficient: e.g. "consultant insurance"
    must not count as coverage for the distinct concept "consultant cyber insurance".
    """
    normalized_target = _normalized_phrase(target)
    if not normalized_target:
        return 0.0
    normalized_article = _normalized_phrase(article_text)
    if normalized_target in normalized_article:
        return 1.0
    return 0.0


def _severity(score: float, threshold: float) -> str:
    if score == 0:
        return "high"
    if score < max(threshold * 0.5, 0.25):
        return "medium"
    return "low"


def _recommendation(category: str, severity: str) -> str:
    if category in {"topic", "heading"}:
        return "add_section" if severity == "high" else "expand_section"
    if category == "keyword":
        return "add_keyword"
    if category == "entity":
        return "add_entity"
    if category == "question":
        return "add_question"
    if category in {"semantic", "coverage"}:
        return "improve_coverage"
    return "improve_coverage"


def _id(prefix: str, payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _lineage(outline_editor: dict[str, Any], semantic_seo: dict[str, Any] | None) -> dict[str, str]:
    required = ("brief_id", "report_id", "decision_id", "strategy_id")
    result = {key: _text(outline_editor.get(key), f"outline_editor.{key}") for key in required}
    for key in ("config_id", "outline_editor_id"):
        value = outline_editor.get(key)
        if value is not None:
            result[key] = _text(value, f"outline_editor.{key}")
    if semantic_seo is not None:
        semantic_id = _text(semantic_seo.get("semantic_id"), "semantic_seo.semantic_id")
        if semantic_seo.get("strategy_id") != result["strategy_id"] or semantic_seo.get("report_id") != result["report_id"] or semantic_seo.get("decision_id") != result["decision_id"]:
            raise ValueError("Semantic SEO lineage does not match Outline Editor")
        result["semantic_id"] = semantic_id
    return result


def _targets(semantic_seo: dict[str, Any] | None, outline_editor: dict[str, Any], details_to_include: dict[str, Any] | None, dataforseo: dict[str, Any] | None) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    if semantic_seo is not None:
        for value in semantic_seo.get("secondary_keywords", []):
            result.append({"category": "keyword", "target": _text(value, "semantic_seo.secondary_keywords[]"), "source": "semantic_seo"})
        for value in semantic_seo.get("semantic_keywords", []):
            result.append({"category": "semantic", "target": _text(value, "semantic_seo.semantic_keywords[]"), "source": "semantic_seo"})
        for value in semantic_seo.get("entities", []):
            result.append({"category": "entity", "target": _text(value, "semantic_seo.entities[]"), "source": "semantic_seo"})
        for value in semantic_seo.get("questions", []):
            result.append({"category": "question", "target": _text(value, "semantic_seo.questions[]"), "source": "semantic_seo"})
    for section in outline_editor.get("sections", []):
        if not isinstance(section, dict):
            raise ValueError("outline_editor.sections[] must be an object")
        if section.get("required") is True:
            result.append({"category": "heading", "target": _text(section.get("heading"), "outline_editor.sections[].heading"), "source": "outline_editor"})
    if details_to_include is not None:
        values = details_to_include.get("details_to_include", [])
        if not isinstance(values, list):
            raise ValueError("details_to_include.details_to_include must be a list")
        for value in values:
            result.append({"category": "coverage", "target": _text(value, "details_to_include.details_to_include[]"), "source": "details_to_include"})
    if dataforseo is not None:
        values = dataforseo.get("competitor_topics", [])
        if not isinstance(values, list):
            raise ValueError("dataforseo.competitor_topics must be a list")
        for value in values:
            result.append({"category": "topic", "target": _text(value, "dataforseo.competitor_topics[]"), "source": "dataforseo"})
    deduped: dict[tuple[str, str], dict[str, str]] = {}
    for item in result:
        key = (item["category"], item["target"].casefold())
        deduped.setdefault(key, item)
    return list(deduped.values())


def build_content_optimization(*, article: dict[str, Any], outline_editor: dict[str, Any], semantic_seo: dict[str, Any] | None = None, details_to_include: dict[str, Any] | None = None, dataforseo: dict[str, Any] | None = None, analysis_mode: str = "coverage", threshold: float = 0.5) -> dict[str, Any]:
    """Build a deterministic content coverage and gap-analysis contract.

    DataForSEO is an upstream evidence provider in v1: callers supply normalized
    competitor topics already discovered by that provider. This engine performs
    no network calls, LLM calls, prose rewriting, or publishing.
    """
    if outline_editor.get("lifecycle_stage") != "outline_editor_ready":
        raise ValueError("Content Optimization requires outline_editor_ready")
    if semantic_seo is not None and semantic_seo.get("lifecycle_stage") != "semantic_seo_ready":
        raise ValueError("Semantic SEO must be semantic_seo_ready")
    if details_to_include is not None and details_to_include.get("lifecycle_stage") != "details_to_include_ready":
        raise ValueError("Details to Include must be details_to_include_ready")
    if analysis_mode not in MODES:
        raise ValueError("analysis_mode must be coverage, competitive, or combined")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    if analysis_mode in {"competitive", "combined"} and dataforseo is None:
        raise ValueError("competitive and combined modes require DataForSEO evidence")
    if dataforseo is not None:
        if dataforseo.get("source") != "dataforseo":
            raise ValueError("dataforseo evidence source must be dataforseo")
        if dataforseo.get("verified") is not True:
            raise ValueError("DataForSEO evidence must be verified")

    title = _text(article.get("title"), "article.title")
    content = _text(article.get("content"), "article.content")
    word_count = article.get("word_count")
    if isinstance(word_count, bool) or not isinstance(word_count, int) or word_count < 1:
        raise ValueError("article.word_count must be a positive integer")
    headings = article.get("headings")
    if not isinstance(headings, list) or any(not isinstance(v, str) or not v.strip() for v in headings):
        raise ValueError("article.headings must be a list of non-empty strings")

    lineage = _lineage(outline_editor, semantic_seo)
    targets = _targets(semantic_seo, outline_editor, details_to_include, dataforseo)
    if analysis_mode == "coverage":
        targets = [item for item in targets if item["source"] != "dataforseo"]
    elif analysis_mode == "competitive":
        targets = [item for item in targets if item["source"] == "dataforseo"]

    article_text = f"{title}\n{content}\n{' '.join(headings)}"
    gaps: list[dict[str, Any]] = []
    for item in targets:
        score = _coverage(item["target"], article_text)
        if score >= threshold:
            continue
        severity = _severity(score, float(threshold))
        evidence = f"coverage={score:.4f}; threshold={float(threshold):.4f}"
        gap_payload = {**item, "coverage_score": score, "severity": severity, "evidence": evidence}
        gaps.append({"gap_id": _id("gap", gap_payload), **gap_payload})

    gaps.sort(key=lambda x: ({"high": 0, "medium": 1, "low": 2}[x["severity"]], x["category"], x["target"].casefold()))
    recommendations: list[dict[str, Any]] = []
    for gap in gaps:
        payload = {"type": _recommendation(gap["category"], gap["severity"]), "target": gap["target"], "priority": gap["severity"]}
        recommendations.append({"recommendation_id": _id("rec", payload), **payload})

    overall = 1.0 if not targets else round(sum(_coverage(item["target"], article_text) for item in targets) / len(targets), 4)
    payload = {"analysis_mode": analysis_mode, "threshold": float(threshold), "article": {"title": title, "content": content, "word_count": word_count, "headings": list(headings)}, "gaps": gaps, "recommendations": recommendations, "summary": {"gap_count": len(gaps), "high_priority_count": sum(g["severity"] == "high" for g in gaps), "coverage_score": overall}}
    return {
        "content_optimization_id": _id("optimization", {"lineage": lineage, **payload, "schema_version": SCHEMA_VERSION, "method_version": METHOD_VERSION}),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": LIFECYCLE_STAGE,
        **payload,
        "audit": {"method": "content_coverage_and_gap_analysis", "method_version": METHOD_VERSION, "validation_status": "validated"},
    }
