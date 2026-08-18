from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .content_brief_agent import run as run_content_brief_agent
from .article_draft import build_article_draft


def _load(project: str, filename: str) -> dict[str, Any]:
    path = Path("research") / project / filename
    return json.loads(path.read_text(encoding="utf-8"))


def _save_if_changed(project: str, filename: str, data: dict[str, Any]) -> None:
    path = Path("research") / project / filename
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if current != data:
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


def run(project_name: str) -> dict[str, Any]:
    """Run the established pipeline and materialize the Article Draft.

    The Writer is strictly downstream of a content_brief_ready artifact. It
    consumes the brief only; upstream research, recommendation, decision and
    strategy artifacts are never recomputed or mutated by the Writer layer.
    """
    run_content_brief_agent(project_name)

    brief = _load(project_name, "content-brief.json")
    draft = build_article_draft(content_brief=brief)
    _save_if_changed(project_name, "article-draft.json", draft)

    metadata_path = Path("research") / project_name / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["project_name"] = project_name
    metadata["status"] = "draft_ready"
    metadata_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")

    return draft
