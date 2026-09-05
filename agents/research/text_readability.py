from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from typing import Any, Callable

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
_SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)")
_VOWEL_RE = re.compile(r"[aeiouy]+")
_LLM_KEYS = {"status", "summary", "strengths", "issues"}


class ReadabilityLLMProviderProtocol:
    """Documentation-only protocol shape for an injected LLM evaluator."""

    def assess(self, *, text: str, local_metrics: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _ready(document: dict[str, Any], lifecycle: str, label: str) -> None:
    if document.get("lifecycle_stage") != lifecycle:
        raise ValueError(f"Text Readability requires {lifecycle} {label}")


def _lineage(article_draft: dict[str, Any]) -> dict[str, str]:
    fields = ("draft_id", "brief_id", "report_id", "decision_id", "strategy_id")
    result: dict[str, str] = {}
    for field in fields:
        value = _clean(article_draft.get(field))
        if not value:
            raise ValueError(f"Article Draft requires {field}")
        result[field] = value
    return result


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_RE.findall(text) if _words(part)]


def _syllables(word: str) -> int:
    normalized = re.sub(r"[^a-z]", "", word.lower())
    if not normalized:
        return 0
    groups = len(_VOWEL_RE.findall(normalized))
    if normalized.endswith("e") and not normalized.endswith(("le", "ye")) and groups > 1:
        groups -= 1
    if normalized.endswith("ed") and len(normalized) > 2 and groups > 1 and not normalized.endswith(("ted", "ded")):
        groups -= 1
    return max(1, groups)


def analyze_readability(text: str) -> dict[str, Any]:
    """Calculate deterministic English readability metrics with the Python stdlib only."""
    clean_text = _clean(text)
    words = _words(clean_text)
    sentences = _sentences(clean_text)
    sentence_count = max(1, len(sentences)) if words else 0
    word_count = len(words)
    syllable_count = sum(_syllables(word) for word in words)
    avg_sentence_words = round(word_count / sentence_count, 2) if sentence_count else 0.0
    avg_syllables_word = round(syllable_count / word_count, 2) if word_count else 0.0

    if word_count and sentence_count:
        fre = 206.835 - 1.015 * avg_sentence_words - 84.6 * avg_syllables_word
        grade = 0.39 * avg_sentence_words + 11.8 * avg_syllables_word - 15.59
    else:
        fre = 0.0
        grade = 0.0

    return {
        "word_count": word_count,
        "sentence_count": len(sentences),
        "syllable_count": syllable_count,
        "average_sentence_words": avg_sentence_words,
        "average_syllables_per_word": avg_syllables_word,
        "flesch_reading_ease": round(fre, 2),
        "flesch_kincaid_grade": round(grade, 2),
    }


def _local_outcome(metrics: dict[str, Any], *, target_grade: float = 10.0) -> str:
    if metrics["word_count"] == 0:
        return "needs_revision"
    return "passed" if metrics["flesch_kincaid_grade"] <= target_grade else "needs_revision"


def _provider_assessment(provider: Any, text: str, metrics: dict[str, Any]) -> dict[str, Any]:
    if provider is None:
        return {"status": "not_requested", "summary": "No LLM readability assessment was requested."}
    assessor: Callable[..., Any] | None = getattr(provider, "assess", None)
    if assessor is None or not callable(assessor):
        raise ValueError("Text Readability LLM provider must expose assess(text=..., local_metrics=...)")
    result = assessor(text=text, local_metrics=copy.deepcopy(metrics))
    if not isinstance(result, dict):
        raise ValueError("Text Readability LLM provider must return an object")
    unknown = set(result) - _LLM_KEYS
    if unknown:
        raise ValueError(f"Unsupported Text Readability LLM assessment fields: {sorted(unknown)}")
    status = _clean(result.get("status")) or "provided"
    if status not in {"provided", "not_requested"}:
        raise ValueError("Unsupported Text Readability LLM assessment status")
    for field in ("strengths", "issues"):
        if field in result and (not isinstance(result[field], list) or not all(isinstance(item, str) and item.strip() for item in result[field])):
            raise ValueError(f"Text Readability LLM assessment {field} must be an array of non-empty strings")
    if "summary" in result and not isinstance(result["summary"], str):
        raise ValueError("Text Readability LLM assessment summary must be a string")
    return copy.deepcopy(result) | {"status": status}


def _id(lineage: dict[str, str], local_metrics: dict[str, Any], outcome: str, llm_assessment: dict[str, Any]) -> str:
    raw = json.dumps({"lineage": lineage, "local_metrics": local_metrics, "outcome": outcome, "llm_assessment": llm_assessment}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"readability_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def build_text_readability(*, article_draft: dict[str, Any], llm_provider: Any = None, target_grade: float = 10.0) -> dict[str, Any]:
    """Build a readability contract from local metrics plus an optional injected LLM assessment."""
    _ready(article_draft, "draft_ready", "Article Draft")
    lineage = _lineage(article_draft)
    if isinstance(target_grade, bool) or not isinstance(target_grade, (int, float)) or not math.isfinite(target_grade) or target_grade <= 0:
        raise ValueError("target_grade must be a positive finite number")

    sections = article_draft.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("Article Draft.sections is required and must be non-empty")
    bodies = [_clean(section.get("body")) for section in sections if isinstance(section, dict)]
    text = "\n\n".join(body for body in bodies if body)
    if not text:
        raise ValueError("Article Draft must contain non-empty section body text")

    metrics = analyze_readability(text)
    outcome = _local_outcome(metrics, target_grade=float(target_grade))
    llm_assessment = _provider_assessment(llm_provider, text, metrics)
    return {
        "text_readability_id": _id(lineage, metrics, outcome, llm_assessment),
        **lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "text_readability_ready",
        "outcome": outcome,
        "local_metrics": metrics,
        "llm_assessment": llm_assessment,
        "target_grade": float(target_grade),
        "constraints": {
            "network_access": False,
            "provider_call": llm_provider is not None,
            "source_mutation": False,
            "draft_mutation": False,
        },
        "audit": {
            "method": "local_readability_metrics_plus_injected_llm_assessment",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }
