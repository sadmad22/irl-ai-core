from __future__ import annotations

import re
from collections import Counter
from typing import Any

METHOD_VERSION = "entity-v1"


def analyze_entities(serp_analysis: dict[str, Any]) -> dict[str, Any]:
    """Extract a deterministic minimum entity inventory from SERP results.

    This v1 intentionally treats ranked result domains as organization entities
    and records mention/relevance signals from titles/snippets. It does not
    claim external entity knowledge or identity resolution.
    """
    results = serp_analysis.get("results", []) or []
    entities: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in results:
        domain = str(result.get("domain", "")).strip().lower()
        if not domain or domain in seen:
            continue
        seen.add(domain)
        text = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        token_hits = len(re.findall(r"\b(?:insurance|health|medical|expat|consultant|accountant|nurse|cyber|business|professional)\b", text))
        position = result.get("position")
        try:
            position_score = 1.0 / max(1, int(position or len(entities) + 1))
        except (TypeError, ValueError):
            position_score = 0.0
        relevance = min(1.0, 0.5 * position_score + 0.1 * token_hits)
        entities.append({
            "entity_id": domain,
            "entity_type": "organization",
            "mentioned": True,
            "relevance": round(relevance, 4),
            "source_position": position,
        })

    return {
        "entities": entities,
        "entity_count": len(entities),
        "unique_domains": len(seen),
        "method": METHOD_VERSION,
    }
