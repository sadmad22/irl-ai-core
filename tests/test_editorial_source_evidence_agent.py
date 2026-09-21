from __future__ import annotations

import json

from agents.research.editorial_source_evidence_agent import run


def test_materializes_editorial_evidence_from_explicit_source_pages(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "research" / "e2e-project"
    root.mkdir(parents=True)

    (root / "entity-evidence.json").write_text(
        json.dumps([{"evidence_id": "ev_1"}]),
        encoding="utf-8",
    )
    (root / "editorial-source-pages.json").write_text(
        json.dumps(
            {
                "ev_1": {
                    "section_index": 2,
                    "url": "https://example.com/guide",
                    "title": "Expat Health Insurance Guide",
                    "domain": "example.com",
                    "text": "International health insurance can provide coverage across multiple countries.",
                    "verification": "page_reviewed",
                }
            }
        ),
        encoding="utf-8",
    )

    result = run("e2e-project")

    assert result[0]["evidence_id"] == "ev_1"
    assert result[0]["status"] == "ready"
    assert result[0]["provenance"]["verification"] == "page_reviewed"

    saved = json.loads((root / "editorial-evidence.json").read_text(encoding="utf-8"))
    assert saved == result


def test_materialization_preserves_snippet_only_as_candidate(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "research" / "e2e-project"
    root.mkdir(parents=True)

    (root / "serp-intent-evidence.json").write_text(
        json.dumps([{"evidence_id": "ev_1"}]),
        encoding="utf-8",
    )
    (root / "editorial-source-pages.json").write_text(
        json.dumps(
            [
                {
                    "evidence_id": "ev_1",
                    "section_index": 1,
                    "url": "https://example.com",
                    "title": "Example",
                    "domain": "example.com",
                    "text": "Snippet material.",
                    "verification": "snippet_only",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = run("e2e-project")

    assert result[0]["status"] == "candidate"
    assert result[0]["provenance"]["method"] == "serp-snippet-editorial-v1"


def test_missing_source_pages_keeps_optional_boundary_inactive(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "research" / "e2e-project").mkdir(parents=True)

    assert run("e2e-project") == []
    assert not (tmp_path / "research" / "e2e-project" / "editorial-evidence.json").exists()


def test_invalid_section_metadata_fails_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "research" / "e2e-project"
    root.mkdir(parents=True)

    (root / "authority-evidence.json").write_text(
        json.dumps([{"evidence_id": "ev_1"}]),
        encoding="utf-8",
    )
    (root / "editorial-source-pages.json").write_text(
        json.dumps(
            {
                "ev_1": {
                    "url": "https://example.com",
                    "title": "Example",
                    "domain": "example.com",
                    "text": "Source material.",
                    "verification": "page_reviewed",
                }
            }
        ),
        encoding="utf-8",
    )

    import pytest

    with pytest.raises(ValueError, match="section_index"):
        run("e2e-project")
