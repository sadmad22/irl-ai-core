from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .content_brief_agent import run as run_content_brief_agent
from .article_draft import build_article_draft


def _load(project: str, filename: str) -> dict[str, Any]:
    path = Path("research") / project / filename
    return json.loads(path.read_text(encoding="utf-8"))


def _load_evidence_records(project: str) -> list[dict[str, Any]]:
    root = Path("research") / project
    records: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        if "evidence" not in path.stem:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, list):
            records.extend(item for item in data if isinstance(item, dict) and item.get("evidence_id"))
        elif isinstance(data, dict) and data.get("evidence_id"):
            records.append(data)
    return sorted(records, key=lambda item: str(item["evidence_id"]))


def _load_serp_results(project: str) -> list[dict[str, Any]]:
    path = Path("research") / project / "serp-analysis.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    results = data.get("results") if isinstance(data, dict) else None
    return [item for item in results if isinstance(item, dict)] if isinstance(results, list) else []


def _load_source_evidence(project: str) -> list[dict[str, Any]]:
    path = Path("research") / project / "source-evidence.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict) and item.get("evidence_id")]
    return [data] if isinstance(data, dict) and data.get("evidence_id") else []


def _faq_editorial_evidence(source_evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    questions = {
        "editorial_page_hartford_faq_workflow_20260825": "How does professional liability insurance work?",
        "editorial_page_hartford_faq_coverage_20260825": "What does professional liability insurance cover?",
        "editorial_page_hartford_faq_need_20260825": "Who needs professional liability insurance?",
        "editorial_page_insureon_faq_consultants_20260825": "Do consultants need professional liability insurance?",
    }
    selected: list[dict[str, Any]] = []
    for item in source_evidence:
        evidence_id = str(item.get("evidence_id", "")).strip()
        if int(item.get("section_index", 0) or 0) != 6 or evidence_id not in questions:
            continue
        if str(item.get("provenance", {}).get("verification", "")) != "page_reviewed":
            continue
        text = str(item.get("text", "")).strip()
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        url = str(source.get("url", "")).strip()
        if not text or not url:
            continue
        record = dict(item)
        record["status"] = "ready"
        selected.append(record)
    return sorted(selected, key=lambda item: (list(questions).index(str(item["evidence_id"])), str(item["evidence_id"])))


def _apply_faq_editorial_evidence(draft: dict[str, Any], source_evidence: list[dict[str, Any]]) -> None:
    faq_evidence = _faq_editorial_evidence(source_evidence)
    if not faq_evidence:
        return

    faq_section = next(
        (section for section in draft.get("sections", []) if str(section.get("heading", "")).strip().lower() == "frequently asked questions"),
        None,
    )
    if faq_section is None:
        return

    paragraphs = [
        f"{questions}: {item['text']}"
        for item, questions in [
            (item, {"editorial_page_hartford_faq_workflow_20260825": "How does professional liability insurance work?", "editorial_page_hartford_faq_coverage_20260825": "What does professional liability insurance cover?", "editorial_page_hartford_faq_need_20260825": "Who needs professional liability insurance?", "editorial_page_insureon_faq_consultants_20260825": "Do consultants need professional liability insurance?"}[item["evidence_id"]])
            for item in faq_evidence
        ]
    ]
    faq_section["body"] = "\n\n".join(paragraphs)
    faq_section["evidence_refs"] = [str(item["evidence_id"]) for item in faq_evidence]
    faq_section["claims"] = []
    for item in faq_evidence:
        text = str(item["text"]).strip()
        digest = hashlib.sha256(f"6:{item['evidence_id']}:{text}".encode("utf-8")).hexdigest()[:12]
        faq_section["claims"].append({
            "claim_id": f"claim_6_{digest}",
            "text": text,
            "evidence_refs": [str(item["evidence_id"])],
            "grounding_status": "grounded",
        })

    editorial = draft.setdefault("editorial_evidence", [])
    existing = {str(item.get("evidence_id", "")) for item in editorial if isinstance(item, dict)}
    for item in faq_evidence:
        if item["evidence_id"] not in existing:
            editorial.append(item)

    draft["evidence_refs"] = list(dict.fromkeys(
        [str(ref) for ref in draft.get("evidence_refs", []) if str(ref).strip()]
        + [str(item["evidence_id"]) for item in faq_evidence]
    ))
    contracts = draft.get("section_evidence_contracts", [])
    for contract in contracts:
        if int(contract.get("section_index", 0) or 0) == 6:
            contract["status"] = "ready"
            contract["evidence_refs"] = [str(item["evidence_id"]) for item in faq_evidence]
            break


def _save_if_changed(project: str, filename: str, data: dict[str, Any]) -> None:
    path = Path("research") / project / filename
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if current != data:
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


def run(project_name: str) -> dict[str, Any]:
    """Run Content Brief then materialize an evidence-grounded Article Draft."""
    run_content_brief_agent(project_name)

    brief = _load(project_name, "content-brief.json")
    evidence_records = _load_evidence_records(project_name)
    serp_results = _load_serp_results(project_name)
    source_evidence = _load_source_evidence(project_name)
    draft = build_article_draft(
        content_brief=brief,
        evidence_records=evidence_records,
        serp_results=serp_results,
        source_evidence=source_evidence,
    )
    _apply_faq_editorial_evidence(draft, source_evidence)
    _save_if_changed(project_name, "article-draft.json", draft)

    metadata_path = Path("research") / project_name / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["project_name"] = project_name
    metadata["status"] = "draft_ready"
    metadata_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")

    return draft
