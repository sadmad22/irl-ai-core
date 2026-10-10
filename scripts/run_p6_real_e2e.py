#!/usr/bin/env python3
"""Temporary P6 real E2E runner. Uses cached research artifacts and never publishes."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

PROJECT = os.environ.get("P6_PROJECT", "e2e-nurse-insurance")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")
ROOT = Path("research") / PROJECT
SUMMARY_PATH = Path("/tmp/p6-real-e2e-summary.json")
API_URL = "https://api.openai.com/v1/responses"


def _writer_response_schema(section_count: int) -> dict[str, Any]:
    """Build a strict Responses API schema bound to the current outline length."""
    if section_count < 1:
        raise ValueError("P6 writer requires at least one input section")
    indexes = list(range(section_count))

    return {
        "type": "object",
        "properties": {
            "sections": {
                "type": "array",
                "minItems": section_count,
                "maxItems": section_count,
                "items": {
                    "type": "object",
                    "properties": {
                        "section_index": {"type": "integer", "enum": indexes},
                        "body": {"type": "string"},
                    },
                    "required": ["section_index", "body"],
                    "additionalProperties": False,
                },
            },
            "tables": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "table_id": {"type": "string"},
                        "title": {"type": "string"},
                        "section_index": {"type": "integer", "enum": indexes},
                        "columns": {"type": "array", "items": {"type": "string"}},
                        "rows": {
                            "type": "array",
                            "items": {"type": "array", "items": {"type": "string"}},
                        },
                        "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "table_id", "title", "section_index", "columns", "rows", "evidence_refs"
                    ],
                    "additionalProperties": False,
                },
            },
            "images": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "image_id": {"type": "string"},
                        "section_index": {"type": "integer", "enum": indexes},
                        "placement": {"type": "string"},
                        "prompt": {"type": "string"},
                        "alt_text": {"type": "string"},
                        "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "image_id", "section_index", "placement", "prompt", "alt_text", "evidence_refs"
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["sections", "tables", "images"],
        "additionalProperties": False,
    }


def _writer_instructions(section_count: int) -> str:
    """Build the evidence-constrained writer prompt without making a provider call."""
    if section_count < 1:
        raise ValueError("P6 writer requires at least one input section")
    return f"""You are the evidence-constrained article writer for Insurance Review Lab.
Return ONLY valid JSON with exactly top-level keys sections, tables, images.
Return exactly {section_count} section items, in the same order as the input, with section_index
values exactly 0 through {section_count - 1}; never omit or repeat an input section.
Each item has only section_index and body. A sparse section still needs a short, cautious body.
Use only evidence assigned to that section. Every factual, numerical, provider, coverage,
price, comparison, recommendation, or methodology statement must be directly supported.
Omit unsupported statements; do not guess, add generic advice, or invent FAQ pairs.
Prefer 180-300 words per section; never exceed 350 words in a section. Use less
when assigned evidence is sparse, and avoid repeating facts across sections.
When assigned evidence contains a search-intent distribution, preserve the recorded category
labels and provided values. Do not infer reader behavior or purchases from those categories
(for example, do not claim that readers are purchasing coverage unless directly supported).
Keep independent factual propositions in separate sentences when they rely on different evidence
records. In particular, report search-intent distribution values, the dominant category, and
mixed-intent status in separate sentences so each claim can be grounded to its specific evidence.
Do not add generic comparison advice such as "Coverage details should also be compared."
Instead state the specific coverage features supported by assigned evidence, or omit the advice.
In sources/methodology sections, do not narrate what "the article uses evidence for", list
article topics as a methodology claim, or claim a process was used unless assigned evidence
explicitly documents that process. Describe only supported source, provenance, and lineage facts.
Preserve source-specific terminology when describing policy forms and coverage features; do
not replace a concrete source term with an unsupported generalization.
Do not add a sentence that only announces or points to a following table
(for example, "The comparison points are summarized below."); let the structured
table stand on its own and include only evidence-supported prose in the section body.
Do not expose internal IDs or research metadata. Do not generate headings.
tables must be an array; only include evidence-supported tables with fields
table_id,title,section_index,columns,rows,evidence_refs. Comparison/buyer_guide requires a table.
images must be a non-empty array of objects with exactly image_id,section_index,placement,
prompt,alt_text,evidence_refs. Do not provide image URLs or claim media was generated.
No markdown fences or text outside the JSON object."""


class RealOpenAIArticleWriter:
    """Injected real OpenAI writer implementing the repository's writer protocol."""

    def __init__(self, content_type: str, primary_keyword: str) -> None:
        self.content_type = content_type
        self.primary_keyword = primary_keyword

    def write(self, *, sections: list[dict[str, Any]], editorial_rules: dict[str, Any]) -> dict[str, Any]:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing; no request was sent")

        instructions = _writer_instructions(len(sections))
        payload = {
            "content_type": self.content_type,
            "primary_keyword": self.primary_keyword,
            "sections": sections,
            "editorial_rules": editorial_rules,
        }
        max_output_tokens = int(os.environ.get("P6_OPENAI_MAX_OUTPUT_TOKENS", "12000"))
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "instructions": instructions,
                "input": json.dumps(payload, ensure_ascii=False),
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "irl_p6_article_writer",
                        "strict": True,
                        "schema": _writer_response_schema(len(sections)),
                    }
                },
                "max_output_tokens": max_output_tokens,
            },
            timeout=int(os.environ.get("P6_OPENAI_TIMEOUT_SECONDS", "180")),
        )
        if not response.ok:
            try:
                message = response.json().get("error", {}).get("message")
            except (ValueError, AttributeError):
                message = None
            raise RuntimeError(f"OpenAI writer request failed: HTTP {response.status_code}" + (f": {message}" if message else ""))

        data = response.json()
        response_id = data.get("id")
        response_status = data.get("status")
        incomplete_details = data.get("incomplete_details") or {}
        incomplete_reason = incomplete_details.get("reason")
        usage = data.get("usage") or {}
        output_tokens = usage.get("output_tokens")

        # Do not attempt to parse partial text from an incomplete Response.
        if response_status != "completed":
            raise RuntimeError(
                "OpenAI response was not completed: "
                f"status={response_status!r}; reason={incomplete_reason!r}; "
                f"output_tokens={output_tokens!r}; max_output_tokens={max_output_tokens}; "
                f"response_id={response_id!r}"
            )

        output = data.get("output_text")
        if not isinstance(output, str) or not output.strip():
            chunks = [
                block["text"]
                for item in data.get("output", [])
                if isinstance(item, dict)
                for block in item.get("content", [])
                if isinstance(block, dict) and block.get("type") == "output_text" and isinstance(block.get("text"), str)
            ]
            output = "\n".join(chunks)
        if not isinstance(output, str) or not output.strip():
            raise RuntimeError("OpenAI returned no writer output")
        try:
            result = json.loads(output)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "OpenAI writer returned invalid JSON: "
                f"response_id={response_id!r}; status={response_status!r}; "
                f"output_chars={len(output)}; line={exc.lineno}; column={exc.colno}; "
                f"output_tokens={output_tokens!r}; incomplete_reason={incomplete_reason!r}"
            ) from exc
        if not isinstance(result, dict):
            raise RuntimeError("OpenAI writer output must be a JSON object")

        returned_sections = result.get("sections")
        actual_indexes = [
            item.get("section_index")
            for item in returned_sections
            if isinstance(item, dict)
        ] if isinstance(returned_sections, list) else []
        expected_indexes = list(range(len(sections)))
        if (
            not isinstance(returned_sections, list)
            or len(returned_sections) != len(sections)
            or actual_indexes != expected_indexes
        ):
            actual_count = len(returned_sections) if isinstance(returned_sections, list) else None
            raise RuntimeError(
                "OpenAI writer section contract mismatch: "
                f"expected_count={len(sections)}; actual_count={actual_count}; "
                f"expected_indexes={expected_indexes}; actual_indexes={actual_indexes}; "
                f"response_id={response_id!r}; status={response_status!r}; "
                f"output_tokens={output_tokens!r}"
            )
        return result


def load(name: str) -> dict[str, Any]:
    path = ROOT / name
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected JSON object in {path}")
    return data


def main() -> int:
    print("=== REAL P6 E2E START ===", flush=True)
    print("project =", PROJECT, flush=True)
    print("openai_model =", MODEL, flush=True)
    try:
        if not ROOT.is_dir():
            raise RuntimeError(f"Project artifact directory not found: {ROOT}")
        missing = [name for name in ("keyword.json", "search-metrics.json", "serp-analysis.json") if not (ROOT / name).is_file()]
        if missing:
            raise RuntimeError("Missing cached artifacts; stopping before any provider calls: " + ", ".join(missing))
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise RuntimeError("OPENAI_API_KEY is missing; no API request was sent")
        metrics, serp = load("search-metrics.json"), load("serp-analysis.json")
        if not metrics.get("provider") or not serp.get("provider"):
            raise RuntimeError("Cached metrics/SERP must identify their providers; refusing to proceed")

        # Import only after fail-closed preflight. Research Agent reuses existing metrics/SERP.
        from agents.research.content_research_pipeline import run_content_research_to_wordpress_draft

        brief = load("content-brief.json")
        result = run_content_research_to_wordpress_draft(
            PROJECT,
            llm_provider=RealOpenAIArticleWriter(
                str(brief.get("content_type", "guide")),
                str(brief.get("primary_keyword", "")),
            ),
            deliver=False,
        )
        quality = result.get("article_draft_quality", {})
        audit = result.get("claim_audit", {})
        publication = result.get("publication", {})
        delivery = result.get("wordpress_draft_delivery", {})
        summary = {
            "project": PROJECT,
            "model": MODEL,
            "research_artifacts_reused": True,
            "provider_api_calls_expected": "OpenAI writer only; cached metrics/SERP required",
            "search_metrics_provider": load("search-metrics.json").get("provider"),
            "serp_provider": load("serp-analysis.json").get("provider"),
            "serp_position_semantics": load("serp-analysis.json").get("position_semantics"),
            "metadata_status": load("metadata.json").get("status"),
            "article_draft_quality": quality.get("outcome"),
            "article_draft_quality_findings": quality.get("findings", []),
            "claim_audit": audit.get("outcome"),
            "seo_validation": result.get("seo_validation", {}).get("outcome"),
            "editorial_review": result.get("editorial_review", {}).get("outcome"),
            "publication_gate": publication.get("gate_status"),
            "wordpress_delivery": {
                "execution_mode": delivery.get("execution_mode"),
                "delivery_status": delivery.get("delivery_status"),
            },
            "wordpress_delivery_enabled": False,
        }
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print("=== P6 SUMMARY ===", flush=True)
        print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
        print("summary_file =", SUMMARY_PATH, flush=True)
        return 0
    except Exception as exc:
        error = {"project": PROJECT, "model": MODEL, "error_type": type(exc).__name__, "error_message": str(exc)}
        SUMMARY_PATH.write_text(json.dumps(error, indent=2, ensure_ascii=False), encoding="utf-8")
        print("=== P6 ERROR ===", flush=True)
        print(json.dumps(error, indent=2, ensure_ascii=False), flush=True)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
