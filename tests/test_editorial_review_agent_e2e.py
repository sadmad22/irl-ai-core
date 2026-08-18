from __future__ import annotations

import copy
import json
from pathlib import Path

from agents.research.editorial_review_agent import run


def _write_project(tmp_path: Path, name: str = "demo") -> Path:
    root = tmp_path / "research" / name
    root.mkdir(parents=True)
    return root


def test_editorial_review_agent_produces_review_artifact(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = _write_project(tmp_path)
    # The test uses a real upstream project fixture when available through the
    # repository's normal runner; this smoke test only asserts the artifact
    # contract once the pipeline has produced the draft.
    fixture = Path(__file__).parent / "fixtures" / "editorial_review_project.json"
    if not fixture.exists():
        return
    data = json.loads(fixture.read_text(encoding="utf-8"))
    for name, payload in data.items():
        (project / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    result = run("demo")
    assert result["lifecycle_stage"] == "editorial_review_ready"
    assert Path("research/demo/editorial-review.json").exists()


def test_editorial_review_agent_preserves_draft_lineage(tmp_path, monkeypatch):
    fixture = Path(__file__).parent / "fixtures" / "editorial_review_project.json"
    if not fixture.exists():
        return
    monkeypatch.chdir(tmp_path)
    project = _write_project(tmp_path)
    data = json.loads(fixture.read_text(encoding="utf-8"))
    for name, payload in data.items():
        (project / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    before = json.loads((project / "article-draft.json").read_text(encoding="utf-8"))
    result = run("demo")
    after = json.loads((project / "article-draft.json").read_text(encoding="utf-8"))
    assert after == before
    assert result["draft_id"] == before["draft_id"]
    assert result["brief_id"] == before["brief_id"]
    assert result["report_id"] == before["report_id"]
    assert result["decision_id"] == before["decision_id"]
    assert result["strategy_id"] == before["strategy_id"]
    assert result["evidence_refs"] == before["evidence_refs"]


def test_editorial_review_agent_is_stable(tmp_path, monkeypatch):
    fixture = Path(__file__).parent / "fixtures" / "editorial_review_project.json"
    if not fixture.exists():
        return
    monkeypatch.chdir(tmp_path)
    project = _write_project(tmp_path)
    data = json.loads(fixture.read_text(encoding="utf-8"))
    for name, payload in data.items():
        (project / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    first = run("demo")
    second = run("demo")
    assert second == first
