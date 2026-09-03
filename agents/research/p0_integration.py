from __future__ import annotations

import hashlib
import json
from typing import Any


SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"

_REQUIRED_LINEAGE = (
    "brief_id",
    "report_id",
    "decision_id",
    "strategy_id",
)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _lineage(source: dict[str, Any], name: str) -> dict[str, str]:
    if not isinstance(source, dict):
        raise ValueError(f"{name} must be an object")

    return {
        key: _text(source.get(key), f"{name}.{key}")
        for key in _REQUIRED_LINEAGE
    }


def _require_lifecycle(
    source: dict[str, Any],
    expected: str,
    name: str,
) -> None:
    if source.get("lifecycle_stage") != expected:
        raise ValueError(
            f"{name} requires lifecycle_stage={expected}"
        )


def _quality_signal(
    article_draft_quality: dict[str, Any],
) -> dict[str, Any]:
    checks = article_draft_quality.get("checks")

    if not isinstance(checks, dict):
        raise ValueError(
            "Article Draft Quality checks must be an object"
        )

    return {
        "available": True,
        "outcome": article_draft_quality.get("outcome"),
        "checks": dict(checks),
        "passed_checks": sum(
            value is True for value in checks.values()
        ),
        "total_checks": len(checks),
        "source": {
            "contract": "article_draft_quality",
            "quality_id": article_draft_quality.get("quality_id"),
        },
    }


def _seo_signal(
    seo_validation: dict[str, Any],
) -> dict[str, Any]:
    checks = seo_validation.get("checks")

    if not isinstance(checks, dict):
        raise ValueError(
            "SEO Validation checks must be an object"
        )

    return {
        "available": True,
        "outcome": seo_validation.get("outcome"),
        "checks": dict(checks),
        "passed_checks": sum(
            value is True for value in checks.values()
        ),
        "total_checks": len(checks),
        "source": {
            "contract": "seo_validation",
            "seo_validation_id": seo_validation.get(
                "seo_validation_id"
            ),
        },
    }


def _semantic_signal(
    semantic_seo: dict[str, Any],
) -> dict[str, Any]:
    semantic_keywords = semantic_seo.get(
        "semantic_keywords", []
    )
    secondary_keywords = semantic_seo.get(
        "secondary_keywords", []
    )
    entities = semantic_seo.get("entities", [])
    questions = semantic_seo.get("questions", [])
    section_map = semantic_seo.get(
        "section_keyword_map", []
    )

    for field, value in (
        ("semantic_keywords", semantic_keywords),
        ("secondary_keywords", secondary_keywords),
        ("entities", entities),
        ("questions", questions),
        ("section_keyword_map", section_map),
    ):
        if not isinstance(value, list):
            raise ValueError(
                f"Semantic SEO {field} must be an array"
            )

    return {
        "available": True,
        "primary_keyword": semantic_seo.get(
            "primary_keyword"
        ),
        "secondary_keyword_count": len(
            secondary_keywords
        ),
        "semantic_keyword_count": len(
            semantic_keywords
        ),
        "entity_count": len(entities),
        "question_count": len(questions),
        "mapped_section_count": len(section_map),
        "source": {
            "contract": "semantic_seo",
            "semantic_id": semantic_seo.get("semantic_id"),
        },
    }


def _serp_signal(
    serp_analysis: dict[str, Any],
) -> dict[str, Any]:
    serp = serp_analysis.get("serp")
    competitor = serp_analysis.get(
        "competitor_analysis"
    )

    if not isinstance(serp, dict):
        raise ValueError("SERP analysis.serp must be an object")

    if not isinstance(competitor, dict):
        raise ValueError(
            "SERP analysis.competitor_analysis must be an object"
        )

    results = serp.get("results")

    if not isinstance(results, list):
        raise ValueError(
            "SERP analysis.serp.results must be an array"
        )

    return {
        "available": True,
        "keyword": serp_analysis.get("keyword"),
        "language": serp_analysis.get("language"),
        "country": serp_analysis.get("country"),
        "result_count": len(results),
        "competitor_analysis": competitor,
        "source": {
            "contract": "serp_analysis",
            "analysis_id": serp_analysis.get("analysis_id"),
        },
    }


def _configuration_signal(
    article_config: dict[str, Any],
) -> dict[str, Any]:
    return {
        "available": True,
        "article_type": article_config.get(
            "article_type"
        ),
        "article_size": article_config.get(
            "article_size"
        ),
        "target_country": article_config.get(
            "target_country"
        ),
        "word_target": dict(
            article_config.get("word_target", {})
        ),
        "heading_target": dict(
            article_config.get("heading_target", {})
        ),
        "h3_target": dict(
            article_config.get("h3_target", {})
        ),
        "source": {
            "contract": "article_configuration",
            "config_id": article_config.get("config_id"),
        },
    }


def _integration_id(
    lineage: dict[str, str],
    signals: dict[str, Any],
) -> str:
    raw = json.dumps(
        {
            "lineage": lineage,
            "signals": signals,
        },
        sort_keys=True,
        ensure_ascii=False,
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:16]

    return f"p0_integration_{digest}"


def build_p0_integration(
    *,
    article_draft_quality: dict[str, Any],
    seo_validation: dict[str, Any],
    semantic_seo: dict[str, Any],
    serp_analysis: dict[str, Any],
    article_config: dict[str, Any],
) -> dict[str, Any]:
    """Aggregate existing P0 contracts into an auditable signal layer.

    This layer does not re-run validation, calculate a Content Score,
    mutate upstream contracts, or perform network access.
    """

    _require_lifecycle(
        article_draft_quality,
        "article_draft_quality_ready",
        "Article Draft Quality",
    )

    _require_lifecycle(
        seo_validation,
        "seo_validation_ready",
        "SEO Validation",
    )

    _require_lifecycle(
        semantic_seo,
        "semantic_seo_ready",
        "Semantic SEO",
    )

    _require_lifecycle(
        serp_analysis,
        "serp_analysis_ready",
        "SERP Analysis",
    )

    _require_lifecycle(
        article_config,
        "article_config_ready",
        "Article Configuration",
    )

    sources = {
        "article_draft_quality": article_draft_quality,
        "seo_validation": seo_validation,
        "semantic_seo": semantic_seo,
        "serp_analysis": serp_analysis,
        "article_configuration": article_config,
    }

    lineage = {
        name: _lineage(source, name)
        for name, source in sources.items()
    }

    expected_lineage = next(iter(lineage.values()))

    for name, source_lineage in lineage.items():
        if source_lineage != expected_lineage:
            raise ValueError(
                f"P0 Integration lineage mismatch: "
                f"{name} does not match the integration lineage"
            )

    signals = {
        "quality": _quality_signal(
            article_draft_quality
        ),
        "seo": _seo_signal(
            seo_validation
        ),
        "semantic": _semantic_signal(
            semantic_seo
        ),
        "competitive": _serp_signal(
            serp_analysis
        ),
        "configuration": _configuration_signal(
            article_config
        ),
    }

    return {
        "integration_id": _integration_id(
            expected_lineage,
            signals,
        ),
        **expected_lineage,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": "p0_integration_ready",
        "signals": signals,
        "content_score": None,
        "audit": {
            "method": "p0_existing_contract_signal_integration",
            "version": METHOD_VERSION,
            "validation_status": "validated",
            "content_score_status": "not_calculated",
        },
    }
