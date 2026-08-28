import json

from agents.research import dataforseo_cost


def test_finish_run_records_exact_balance_delta(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = "cost-test"
    (tmp_path / "research" / project).mkdir(parents=True)

    monkeypatch.setattr(dataforseo_cost, "start_run", lambda provider: {"provider": "dataforseo", "available": True, "balance": 10.0, "captured_at": "2026-08-28T10:00:00+00:00"})
    monkeypatch.setattr(dataforseo_cost, "snapshot", lambda: {"available": True, "balance": 9.876543, "captured_at": "2026-08-28T10:01:00+00:00"})

    result = dataforseo_cost.finish_run(
        project,
        {"provider": "dataforseo", "available": True, "balance": 10.0, "captured_at": "2026-08-28T10:00:00+00:00"},
        "dataforseo",
    )

    assert result["exact"] is True
    assert result["cost"] == 0.123457
    saved = json.loads((tmp_path / "research" / project / "dataforseo-cost.json").read_text())
    assert saved["cost"] == 0.123457


def test_finish_run_refuses_negative_delta(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = "cost-test"
    (tmp_path / "research" / project).mkdir(parents=True)
    monkeypatch.setattr(dataforseo_cost, "start_run", lambda provider: {"available": True, "balance": 11.0, "captured_at": "2026-08-28T10:01:00+00:00"})

    monkeypatch.setattr(dataforseo_cost, "fetch_account", lambda: {"configured": True, "balance": 12.0})

    result = dataforseo_cost.finish_run(
        project,
        {"provider": "dataforseo", "available": True, "balance": 11.0, "captured_at": "2026-08-28T10:00:00+00:00"},
        "dataforseo",
    )

    assert result["exact"] is False
    assert result["cost"] is None
    assert "increased" in result["error"]


def test_mock_provider_never_reports_exact_dataforseo_cost(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = "cost-test"
    (tmp_path / "research" / project).mkdir(parents=True)

    result = dataforseo_cost.finish_run(project, dataforseo_cost.start_run("mock"), "mock")

    assert result["exact"] is False
    assert result["cost"] is None
