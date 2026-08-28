from agents.research.wordpress_config import verify_wordpress_credentials


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_wordpress_credentials_verify(monkeypatch):
    def fake_get(url, headers, timeout):
        assert url == "https://insurancereviewlab.com/wp-json/wp/v2/users/me"
        assert headers["Authorization"].startswith("Basic ")
        assert timeout == 15
        return FakeResponse(200, {"id": 42})

    monkeypatch.setattr("agents.research.wordpress_config.requests.get", fake_get)
    result = verify_wordpress_credentials(
        "https://insurancereviewlab.com/",
        "InsuranceReviewLab",
        "application-password",
    )
    assert result["verified"] is True
    assert result["user_id"] == 42


def test_wordpress_credentials_reject_failed_auth(monkeypatch):
    monkeypatch.setattr(
        "agents.research.wordpress_config.requests.get",
        lambda *args, **kwargs: FakeResponse(401, {"code": "rest_not_logged_in"}),
    )
    result = verify_wordpress_credentials(
        "https://insurancereviewlab.com",
        "wrong",
        "wrong",
    )
    assert result["verified"] is False
    assert result["status_code"] == 401
