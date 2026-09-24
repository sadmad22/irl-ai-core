from __future__ import annotations

from pathlib import Path

import pytest

from agents.research import agent


def test_research_agent_prefers_passage_bound_evidence_when_present(tmp_path, monkeypatch):
    project = tmp_path / "research" / "sample"
    project.mkdir(parents=True)
    (project / agent.PASSAGE_BOUND_SOURCE_MATERIAL_FILE).write_text("{}", encoding="utf-8")

    calls: list[str] = []

    def bridge(*, report_id: str, project_path: Path):
        calls.append("bridge")
        assert report_id == "rr_sample"
        assert project_path == project
        return [{"evidence_id": "ev_bridge"}]

    def legacy(*, report_id: str, project_path: Path):
        calls.append("legacy")
        return [{"evidence_id": "ev_legacy"}]

    monkeypatch.setattr(agent, "build_canonical_evidence_from_file", bridge)
    monkeypatch.setattr(agent, "build_substantive_evidence_from_file", legacy)

    records = agent.build_substantive_evidence_for_project(
        report_id="rr_sample",
        project_path=project,
    )

    assert records == [{"evidence_id": "ev_bridge"}]
    assert calls == ["bridge"]


def test_research_agent_uses_legacy_path_only_when_passage_bound_output_is_absent(
    tmp_path, monkeypatch
):
    project = tmp_path / "research" / "sample"
    project.mkdir(parents=True)

    calls: list[str] = []

    def bridge(*, report_id: str, project_path: Path):
        calls.append("bridge")
        return [{"evidence_id": "ev_bridge"}]

    def legacy(*, report_id: str, project_path: Path):
        calls.append("legacy")
        assert report_id == "rr_sample"
        assert project_path == project
        return [{"evidence_id": "ev_legacy"}]

    monkeypatch.setattr(agent, "build_canonical_evidence_from_file", bridge)
    monkeypatch.setattr(agent, "build_substantive_evidence_from_file", legacy)

    records = agent.build_substantive_evidence_for_project(
        report_id="rr_sample",
        project_path=project,
    )

    assert records == [{"evidence_id": "ev_legacy"}]
    assert calls == ["legacy"]


def test_research_agent_does_not_fallback_when_passage_bound_bridge_fails(
    tmp_path, monkeypatch
):
    project = tmp_path / "research" / "sample"
    project.mkdir(parents=True)
    (project / agent.PASSAGE_BOUND_SOURCE_MATERIAL_FILE).write_text("{}", encoding="utf-8")

    calls: list[str] = []

    def bridge(*, report_id: str, project_path: Path):
        calls.append("bridge")
        raise ValueError("invalid passage-bound material")

    def legacy(*, report_id: str, project_path: Path):
        calls.append("legacy")
        return [{"evidence_id": "ev_legacy"}]

    monkeypatch.setattr(agent, "build_canonical_evidence_from_file", bridge)
    monkeypatch.setattr(agent, "build_substantive_evidence_from_file", legacy)

    with pytest.raises(ValueError, match="invalid passage-bound material"):
        agent.build_substantive_evidence_for_project(
            report_id="rr_sample",
            project_path=project,
        )

    assert calls == ["bridge"]
