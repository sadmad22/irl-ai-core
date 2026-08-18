from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent import run as run_research_agent
from .article_draft_agent import run as run_article_draft_agent
from .editorial_review import build_editorial_review


def _load(project: str, filename: str) -> dict[str, Any]:
    return json.loads((Path("research") / project / filename).read_text(encoding="utf-8"))


def _save_if_changed(project: str, filename: str, data: dict[str, Any]) -> None:
    path = Path("research") / project / filename
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if current != data:
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


def run(project_name: str) -> dict[str, Any]:
    """Run the existing upstream pipeline and then evaluate the Article Draft.

    Editorial Review is downstream-only: it never mutates upstream artifacts,
    creates evidence, changes a decision, or publishes the draft.
    """
    run_research_agent(project_name)
    run_article_draft_agent(project_name)

    draft = _load(project_name, "article-draft.json")
    review = build_editorial_review(article_draft=draft)
    _save_if_changed(project_name, "editorial-review.json", review)

    metadata_path = Path("research") / project_name / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["project_name"] = project_name
    metadata["status"] = "editorial_review_ready"
    metadata_path.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")
    return review
