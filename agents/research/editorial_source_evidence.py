from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _evidence_id(record: dict[str, Any]) -> str:
    value = _text(record.get("evidence_id"))
    if not value:
        raise ValueError("Research Evidence requires evidence_id")
    return value


def build_editorial_evidence(
    *,
    evidence_records: list[dict[str, Any]],
    source_pages: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build reader-facing source material from verified Brave-discovered pages."""
    if not isinstance(evidence_records, list):
        raise ValueError("evidence_records must be a list")
    if not isinstance(source_pages, dict):
        raise ValueError("source_pages must be a dictionary keyed by evidence_id")

    outputs: list[dict[str, Any]] = []
    for record in sorted(evidence_records, key=lambda item: _text(item.get("evidence_id"))):
        evidence_id = _evidence_id(record)
        page = source_pages.get(evidence_id)
        if not isinstance(page, dict):
            continue

        url = _text(page.get("url"))
        title = _text(page.get("title"))
        domain = _text(page.get("domain"))
        source_text = _text(page.get("text"))
        verification = _text(page.get("verification"))
        section_index = page.get("section_index")

        if not url or not title or not domain or not source_text:
            continue
        if verification not in {"snippet_only", "page_reviewed"}:
            raise ValueError(f"Unsupported editorial evidence verification: {verification}")
        if isinstance(section_index, bool) or not isinstance(section_index, int) or section_index < 1:
            raise ValueError("Editorial Source Evidence requires integer section_index >= 1")

        status = "ready" if verification == "page_reviewed" else "candidate"
        method = "serp-page-editorial-v1" if verification == "page_reviewed" else "serp-snippet-editorial-v1"

        outputs.append(
            {
                "evidence_id": evidence_id,
                "section_index": section_index,
                "status": status,
                "text": source_text,
                "source": {
                    "type": "serp_result",
                    "url": url,
                    "title": title,
                    "domain": domain,
                },
                "provenance": {
                    "artifact": "serp-analysis.json",
                    "method": method,
                    "verification": verification,
                },
            }
        )

    return outputs
