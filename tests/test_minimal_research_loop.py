from __future__ import annotations

from agents.research.minimal_research_loop import evaluate_research_sufficiency, run_minimal_research_loop


def test_research_is_complete_when_minimum_contract_is_met():
    result = evaluate_research_sufficiency(
        research_report={"report_id": "report_1"},
        question_analysis={"questions": [{"question": "What is accountant insurance?"}]},
        evidence_records=[{"evidence_id": "e1"}],
    )

    assert result["status"] == "research_complete"
    assert result["passed"] is True
    assert result["checks"] == {
        "research_report": True,
        "research_questions": True,
        "evidence": True,
    }
    assert result["evidence_count"] == 1


def test_research_blocks_when_evidence_is_missing():
    result = evaluate_research_sufficiency(
        research_report={"report_id": "report_1"},
        question_analysis={"questions": [{"question": "What is accountant insurance?"}]},
        evidence_records=[],
    )

    assert result["status"] == "research_blocked"
    assert result["passed"] is False
    assert result["checks"]["evidence"] is False


def test_research_blocks_when_questions_are_missing():
    result = evaluate_research_sufficiency(
        research_report={"report_id": "report_1"},
        question_analysis={"questions": []},
        evidence_records=[{"evidence_id": "e1"}],
    )

    assert result["status"] == "research_blocked"
    assert result["checks"]["research_questions"] is False


def test_minimal_loop_runs_research_once_and_evaluates_artifacts(tmp_path, monkeypatch):
    project = "fixture"
    root = tmp_path / "research" / project
    root.mkdir(parents=True)
    (root / "research-report.json").write_text('{"report_id":"report_1"}', encoding="utf-8")
    (root / "question-analysis.json").write_text('{"questions":[{"question":"What is it?"}]}', encoding="utf-8")
    (root / "question-evidence.json").write_text('[{"evidence_id":"e1"}]', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    calls: list[str] = []
    result = run_minimal_research_loop(project, research_runner=calls.append)

    assert calls == [project]
    assert result["status"] == "research_complete"
    assert result["evidence_count"] == 1
