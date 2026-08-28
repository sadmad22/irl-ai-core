from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1.1"

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "what",
    "when", "where", "which", "who", "why", "with", "do", "does", "you", "your",
    "need", "can", "should", "will", "than", "their", "they", "them", "these",
}


def _score_id(draft_id: str, payload: dict[str, Any]) -> str:
    raw = json.dumps({"draft_id": draft_id, "score": payload}, sort_keys=True, ensure_ascii=False)
    return f"cs_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _text(draft: dict[str, Any]) -> str:
    parts = [str(draft.get("title", ""))]
    for section in draft.get("sections", []):
        if isinstance(section, dict):
            parts.extend([str(section.get("heading", "")), str(section.get("body", ""))])
    return "\n".join(parts)


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", text.lower())


def _tokens(text: str) -> set[str]:
    return {token for token in _words(text) if len(token) > 2}


def _meaningful_tokens(text: str) -> set[str]:
    return {token for token in _tokens(text) if token not in _STOPWORDS}


def _similarity(left: str, right: str) -> float:
    a, b = _meaningful_tokens(left), _meaningful_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _coverage(left: str, right: str) -> float:
    a, b = _meaningful_tokens(left), _meaningful_tokens(right)
    if not a:
        return 0.0
    return len(a & b) / len(a)


def _question_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("text", "question", "query"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return str(value).strip() if value is not None else ""


def _component(score: float, maximum: int) -> dict[str, Any]:
    return {"score": round(max(0.0, min(float(maximum), score)), 2), "max": maximum}


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _status(score: float) -> str:
    if score >= 90:
        return "ready"
    if score >= 80:
        return "ready_with_improvements"
    if score >= 70:
        return "needs_improvement"
    return "not_ready"


def _intent_score(report: dict[str, Any], text: str) -> float:
    intent = str((report.get("search_intent") or {}).get("primary_intent", "")).strip().lower()
    signals = {
        "informational": ("guide", "explain", "what", "how", "cost", "coverage"),
        "commercial": ("compare", "comparison", "best", "provider", "cost", "option"),
        "transactional": ("choose", "buy", "quote", "purchase", "coverage", "cost"),
        "navigational": (),
    }.get(intent, ())
    lower = text.lower()
    if intent == "navigational":
        keyword = str(report.get("keyword", "")).strip().lower()
        return 15.0 if keyword and keyword in lower else 7.5
    if not signals:
        return 7.5
    hits = sum(1 for signal in signals if signal in lower)
    return 15.0 * min(1.0, hits / max(3, len(signals) * 0.6))


def _topic_score(strategy: dict[str, Any], draft: dict[str, Any]) -> tuple[float, list[str]]:
    expected = [str(v).strip() for v in strategy.get("sections", []) if str(v).strip()]
    actual = [str(s.get("heading", "")).strip() for s in draft.get("sections", []) if isinstance(s, dict)]
    if not expected:
        return 15.0, []
    missing: list[str] = []
    covered = 0
    for item in expected:
        if any(_similarity(item, candidate) >= 0.55 or _coverage(item, candidate) >= 0.75 for candidate in actual):
            covered += 1
        else:
            missing.append(item)
    return 15.0 * covered / len(expected), missing


def _entity_score(strategy: dict[str, Any], text: str) -> tuple[float, list[str]]:
    entities = [str(v).strip() for v in strategy.get("entities", []) if str(v).strip()]
    if not entities:
        return 10.0, []
    lower = text.lower()
    covered = [entity for entity in entities if entity.lower() in lower]
    return 10.0 * len(covered) / len(entities), [e for e in entities if e not in covered]


def _question_score(strategy: dict[str, Any], text: str) -> tuple[float, list[str]]:
    questions = [_question_text(v) for v in strategy.get("questions", [])]
    questions = [q for q in questions if q]
    if not questions:
        return 10.0, []
    lower = text.lower()
    text_tokens = _meaningful_tokens(lower)
    covered: list[str] = []
    missing: list[str] = []
    for question in questions:
        phrase_hit = question.lower().rstrip("?") in lower
        tokens = _meaningful_tokens(question)
        overlap = len(tokens & text_tokens) / len(tokens) if tokens else 0.0
        if phrase_hit or overlap >= 0.50:
            covered.append(question)
        else:
            missing.append(question)
    return 10.0 * len(covered) / len(questions), missing


def _depth_score(text: str, section_count: int) -> float:
    word_count = len(_words(text))
    if word_count >= 2400:
        base = 10.0
    elif word_count >= 1800:
        base = 8.5
    elif word_count >= 1400:
        base = 7.0
    elif word_count >= 1000:
        base = 5.5
    elif word_count >= 800:
        base = 4.5
    elif word_count >= 600:
        base = 3.5
    elif word_count >= 400:
        base = 2.5
    else:
        base = 1.0
    if section_count >= 7:
        base = min(10.0, base + 0.5)
    elif section_count >= 5:
        base = min(10.0, base + 0.25)
    return base


def _heading_score(strategy: dict[str, Any], draft: dict[str, Any]) -> float:
    expected = [str(v).strip() for v in strategy.get("sections", []) if str(v).strip()]
    actual = [str(s.get("heading", "")).strip() for s in draft.get("sections", []) if isinstance(s, dict)]
    if not expected:
        return 10.0
    matched = sum(1 for value in expected if any(_similarity(value, item) >= 0.55 for item in actual)) / len(expected)
    hierarchy = min(1.0, len(actual) / len(expected))
    return 10.0 * (0.75 * matched + 0.25 * hierarchy)


def _keyword_score(keyword: str, text: str, title: str) -> float:
    keyword = keyword.strip().lower()
    if not keyword:
        return 0.0
    lower = text.lower()
    occurrences = lower.count(keyword)
    title_hit = keyword in title.lower()
    headings = " ".join(str(s.get("heading", "")) for s in [] )
    words = max(1, len(_words(text)))
    density = occurrences / words
    if not title_hit or occurrences == 0:
        return 4.0 if title_hit else 2.0
    if density <= 0.03:
        return 10.0
    if density <= 0.06:
        return 8.0
    return 5.0


def _serp_score(report: dict[str, Any], draft: dict[str, Any], serp_results: list[dict[str, Any]]) -> float:
    if not serp_results:
        return 5.0
    keyword = str(report.get("keyword", "")).strip()
    draft_text = _text(draft)
    benchmark_items = [item for item in serp_results[:10] if isinstance(item, dict)]
    if not benchmark_items:
        return 5.0
    relevance = []
    for item in benchmark_items:
        competitor_text = " ".join(str(item.get(key, "")) for key in ("title", "snippet", "description"))
        relevance.append(_coverage(competitor_text, draft_text))
    avg_relevance = sum(relevance) / len(relevance)
    keyword_presence = sum(1 for item in benchmark_items if keyword.lower() in str(item.get("title", "")).lower()) / len(benchmark_items) if keyword else 0.0
    domain_count = len({str(item.get("domain", "")).lower() for item in benchmark_items if item.get("domain")})
    return min(10.0, 2.0 + 6.0 * avg_relevance + min(1.5, domain_count / 5.0) + 0.5 * keyword_presence + (1.0 if keyword and keyword.lower() in draft_text.lower() else 0.0))


def _evidence_score(brief: dict[str, Any], draft: dict[str, Any]) -> float:
    brief_refs = {str(v) for v in brief.get("evidence_refs", []) if str(v).strip()}
    draft_refs = {str(v) for v in draft.get("evidence_refs", []) if str(v).strip()}
    if not brief_refs:
        return 5.0
    return 5.0 * len(brief_refs & draft_refs) / len(brief_refs)


def _readability_score(text: str) -> float:
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not sentences:
        return 1.0
    lengths = [len(_words(sentence)) for sentence in sentences]
    avg = sum(lengths) / len(lengths)
    long_ratio = sum(1 for value in lengths if value > 30) / len(lengths)
    avg_paragraph = len(_words(text)) / max(1, len(paragraphs))
    if 12 <= avg <= 22 and long_ratio <= 0.15 and avg_paragraph <= 120:
        return 5.0
    if 10 <= avg <= 25 and long_ratio <= 0.25 and avg_paragraph <= 160:
        return 4.0
    if 8 <= avg <= 30 and long_ratio <= 0.35:
        return 3.0
    return 2.0


def build_content_score(*, research_report: dict[str, Any], content_strategy: dict[str, Any], content_brief: dict[str, Any], article_draft: dict[str, Any], serp_results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Calculate deterministic Content Score v1.1 from existing artifacts.

    Calibration improves semantic heading/question matching, depth thresholds,
    SERP lexical benchmarking, and readability diagnostics. No external API or
    model call is made, and the score remains measurement-only.
    """
    report_id = str(research_report.get("report_id", "")).strip()
    strategy_id = str(content_strategy.get("strategy_id", "")).strip()
    brief_id = str(content_brief.get("brief_id", "")).strip()
    draft_id = str(article_draft.get("draft_id", "")).strip()
    if not all((report_id, strategy_id, brief_id, draft_id)):
        raise ValueError("ResearchReport, ContentStrategy, ContentBrief, and ArticleDraft IDs are required")

    text = _text(article_draft)
    keyword = str(content_strategy.get("primary_keyword", research_report.get("keyword", ""))).strip()
    topic, missing_sections = _topic_score(content_strategy, article_draft)
    entities, missing_entities = _entity_score(content_strategy, text)
    questions, missing_questions = _question_score(content_strategy, text)
    components = {
        "search_intent_alignment": _component(_intent_score(research_report, text), 15),
        "topic_coverage": _component(topic, 15),
        "entity_coverage": _component(entities, 10),
        "question_coverage": _component(questions, 10),
        "content_depth": _component(_depth_score(text, len(article_draft.get("sections", []))), 10),
        "heading_structure": _component(_heading_score(content_strategy, article_draft), 10),
        "keyword_optimization": _component(_keyword_score(keyword, text, str(article_draft.get("title", ""))), 10),
        "serp_benchmark": _component(_serp_score(research_report, article_draft, serp_results or []), 10),
        "evidence_authority": _component(_evidence_score(content_brief, article_draft), 5),
        "readability_quality": _component(_readability_score(text), 5),
    }
    total = round(sum(item["score"] for item in components.values()), 2)
    gaps: list[str] = []
    recommendations: list[str] = []
    if missing_sections:
        gaps.append(f"Missing strategy sections: {', '.join(missing_sections)}")
        recommendations.append("Add the missing strategy sections to improve topic coverage.")
    if missing_entities:
        gaps.append(f"Uncovered entities: {', '.join(missing_entities)}")
        recommendations.append("Address the uncovered research entities where relevant and supported.")
    if missing_questions:
        gaps.append(f"Uncovered questions: {', '.join(missing_questions)}")
        recommendations.append("Answer the uncovered research questions explicitly.")
    if components["content_depth"]["score"] < 8:
        gaps.append("Content depth is below the long-form target.")
        recommendations.append("Expand substantive sections with evidence-backed detail rather than filler.")
    if components["keyword_optimization"]["score"] < 8:
        gaps.append("Primary keyword optimization can be improved.")
        recommendations.append("Use the primary keyword naturally in the title and relevant sections without stuffing.")
    if components["readability_quality"]["score"] < 4:
        gaps.append("Readability needs improvement.")
        recommendations.append("Shorten overly long sentences and improve paragraph clarity.")

    payload = {
        "score": total,
        "grade": _grade(total),
        "status": _status(total),
        "components": components,
        "gaps": gaps,
        "recommendations": recommendations,
        "evidence_refs": list(dict.fromkeys(str(v) for v in article_draft.get("evidence_refs", []) if str(v).strip())),
    }
    return {
        "score_id": _score_id(draft_id, payload),
        "report_id": report_id,
        "strategy_id": strategy_id,
        "brief_id": brief_id,
        "draft_id": draft_id,
        "schema_version": SCHEMA_VERSION,
        "method_version": METHOD_VERSION,
        "lifecycle_stage": "content_score_ready",
        **payload,
        "audit": {
            "method": "deterministic_content_score",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
