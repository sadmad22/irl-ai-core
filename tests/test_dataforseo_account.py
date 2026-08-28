import json

from agents.research import dataforseo_account


def test_fetch_account_parses_balance_and_pricing(monkeypatch):
    payload = {
        "tasks": [
            {
                "status_code": 20000,
                "result": [
                    {
                        "login": "hidden@example.com",
                        "timezone": "UTC",
                        "rates": {
                            "price": {
                                "google": {
                                    "search_volume": {
                                        "live": {
                                            "priority_normal": [
                                                {"cost_type": "per_result", "cost": 0.0001},
                                                {"cost_type": "per_request", "cost": 0.01},
                                            ]
                                        }
                                    }
                                }
                            }
                        },
                        "money": {"total": 50.0, "balance": 47.25, "statistics": {"day": {"total": 2.75}}},
                    }
                ],
            }
        ]
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setenv("DATAFORSEO_LOGIN", "login")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "password")
    monkeypatch.setattr(dataforseo_account, "urlopen", lambda *args, **kwargs: Response())

    result = dataforseo_account.fetch_account()

    assert result["configured"] is True
    assert result["balance"] == 47.25
    assert result["total_deposited"] == 50.0
    assert result["today_spend"] == 2.75
    assert len(result["pricing"]) == 2
    assert result["login"] == "hidden@example.com"


def test_fetch_account_does_not_return_credentials(monkeypatch):
    monkeypatch.delenv("DATAFORSEO_LOGIN", raising=False)
    monkeypatch.delenv("DATAFORSEO_PASSWORD", raising=False)

    result = dataforseo_account.fetch_account()

    assert result["configured"] is False
    assert "login" not in result
    assert "password" not in result
