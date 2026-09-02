from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*")
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in",
    "is", "it", "of", "on", "or", "that", "the", "this", "to", "what", "when", "where",
    "which", "who", "why", "with", "you", "your", "vs", "versus",
}


def _clean(value: Any) -> str:
    return str(value).strip() if isinstance(value, str) else ""


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean(value)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def _tokens(text: str) -> list[str]:
    return [t.casefold() for t in _TOKEN_RE.findall(text) if t.casefold() not in _STOPWORDS]


def _phrases(texts: list[str], primary: str, limit: int = 12) -> list[str]:
    counts: Counter[str] = Counter()
    primary_terms = set(_tokens(primary))
    for text in texts:
        tokens = _tokens(text)
        for size in (2, 3):
            for i in range(len(tokens) - size + 1):
                phrase_tokens = tokens[i : i + size]
                if primary_terms.intersection(phrase_tokens):
                    counts[" ".join(phrase_tokens)] += 1
    ranked = sorted(counts, key=lambda p: (-counts[p], p))
    return [p for p in ranked if p.casefold() != primary.casefold()][:limit]


def _semantic_terms(strategy: dict[str, Any], primary: str) -> list[str]:
    sections = strategy.get("sections") if isinstance(strategy.get("sections"), list) else []
    entities = strategy.get("entities") if isinstance(strategy.get("entities"), list) else []
    questions = strategy.get("questions") if isinstance(strategy.get("questions"), list) else []
    texts = [str(v) for v in [strategy.get("angle", ""), strategy.get("audience", ""), strategy.get("format", "")]]
    texts += [str(v) for v in sections + entities + questions]
    candidates = _phrases(texts, primary)
    # Strategy-native entities are semantic concepts even when they do not form an n-gram.
    return _unique(candidates + [str(v) for v in entities if _clean(v).casefold() != primary.casefold()])[:20]


def _section_map(strategy: dict[str, Any], primary: str, secondary: list[str], semantic: list[str]) -> list[dict[str, Any]]:
    sections = strategy.get("sections")
    if not isinstance(sections, list):
        return []
    pool = [primary] + secondary + semantic
    mapped: list[dict[str, Any]] = []
    for section in sections:
        heading = _clean(section)
        if not heading:
            continue
        section_tokens = set(_tokens(heading))
        ranked = []
        for keyword in pool:
            overlap = section_tokens.intersection(_tokens(keyword))
            if overlap:
                ranked.append((len(overlap), keyword))
        keywords = [keyword for _, keyword in sorted(ranked, key=lambda x: (-x[0], x[1]))[:5]]
        if not keywords:
            keywords = [primary]
        mapped.append({"section": heading, "keywords": _unique(keywords)})
    return mapped


def _semantic_id(strategy_id: str, payload: dict[str, Any]) -> str:
    raw = json.dumps({"strategy_id": strategy_id, "semantic": payload}, sort_keys=True)
    return f"sem_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_semantic_seo(*, content_strategy: dict[str, Any], keyword_metrics_provider: Any = None, language: str = "en", country: str | None = None) -> dict[str, Any]:
    """Build a deterministic Semantic SEO contract from a ready Content Strategy.

    The optional keyword-metrics provider enriches the contract with metrics; it
    never supplies or changes the semantic extraction itself. No network call is
    made unless a provider is explicitly supplied by the caller.
    """
    strategy_id = _clean(content_strategy.get("strategy_id"))
    report_id = _clean(content_strategy.get("report_id"))
    decision_id = _clean(content_strategy.get("decision_id"))
    if not strategy_id:
        raise ValueError("Content Strategy.strategy_id is required")
    if content_strategy.get("lifecycle_stage") != "content_strategy_ready":
        raise ValueError("Semantic SEO requires a content_strategy_ready Content Strategy")
    if not report_id or not decision_id:
        raise ValueError("Content Strategy.report_id and decision_id are required")

    primary = _clean(content_strategy.get("primary_keyword"))
    if not primary:
        raise ValueError("Content Strategy.primary_keyword is required")

    sections = content_strategy.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("Content Strategy.sections must be a non-empty list")

    secondary = _unique([str(v) for v in content_strategy.get("entities", []) if _clean(v)])[:12]
    semantic = _semantic_terms(content_strategy, primary)
    questions = _unique([str(v) for v in content_strategy.get("questions", []) if _clean(v)])
    section_map = _section_map(content_strategy, primary, secondary, semantic)

    metrics = None
    if keyword_metrics_provider is not None:
        if not _clean(language):
            raise ValueError("language is required when using keyword metrics")
        if not _clean(country):
            raise ValueError("country is required when using keyword metrics")
        metrics = keyword_metrics_provider.get_metrics(primary, language, country)
        if not isinstance(metrics, dict):
            raise ValueError("Keyword metrics provider must return a dict")
        metrics = dict(metrics)

    payload = {
        "primary_keyword": primary,
        "secondary_keywords": secondary,
        "semantic_keywords": semantic,
        "entities": _unique([str(v) for v in content_strategy.get("entities", [])]),
        "questions": questions,
        "section_keyword_map": section_map,
        "keyword_metrics": metrics,
    }
    result = {
        "semantic_id": _semantic_id(strategy_id, payload),
        "strategy_id": strategy_id,
        "report_id": report_id,
        "decision_id": decision_id,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "semantic_seo_ready",
        **payload,
        "audit": {
            "method": "content_strategy_to_semantic_seo",
            "version": METHOD_VERSION,
            "validation_status": "validated",
            "metrics_enrichment": metrics is not None,
        },
    }
    return result
