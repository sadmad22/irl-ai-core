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


class RealOpenAIArticleWriter:
    """Injected real OpenAI writer implementing the repository's writer protocol."""

    def __init__(self, content_type: str, primary_keyword: str) -> None:
        self.content_type = content_type
        self.primary_keyword = primary_keyword

    def write(self, *, sections: list[dict[str, Any]], editorial_rules: dict[str, Any]) -> dict[str, Any]:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing; no request was sent")

        instructions = """You are the evidence-constrained article writer for Insurance Review Lab.
Return ONLY valid JSON with exactly top-level keys sections, tables, images.
Return one {section_index, body} for each input section, using zero-based indexes.
Use only evidence assigned to that section. Every factual, numerical, provider, coverage,
price, comparison, recommendation, or methodology statement must be directly supported.
Omit unsupported statements; do not guess, add generic advice, or invent FAQ pairs.
Do not expose internal IDs or research metadata. Do not generate headings.
tables must be an array; only include evidence-supported tables with fields
table_id,title,section_index,columns,rows,evidence_refs. Comparison/buyer_guide requires a table.
images must be a non-empty array of objects with exactly image_id,section_index,placement,
prompt,alt_text,evidence_refs. Do not provide image URLs or claim media was generated.
No markdown fences or text outside the JSON object."""
        payload = {
            "content_type": self.content_type,
            "primary_keyword": self.primary_keyword,
            "sections": sections,
            "editorial_rules": editorial_rules,
        }
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "instructions": instructions,
                "input": json.dumps(payload, ensure_ascii=False),
                "text": {"format": {"type": "json_object"}},
                "max_output_tokens": int(os.environ.get("P6_OPENAI_MAX_OUTPUT_TOKENS", "12000")),
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
            raise RuntimeError("OpenAI writer returned invalid JSON") from exc
        if not isinstance(result, dict):
            raise RuntimeError("OpenAI writer output must be a JSON object")
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
