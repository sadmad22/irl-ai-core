from __future__ import annotations

import os

import pytest

from scripts.run_pipeline import _assert_draft_contract, _missing_wordpress_env


def test_missing_wordpress_env_reports_all_required_names(monkeypatch):
    for name in (
        "WORDPRESS_BASE_URL",
        "WORDPRESS_USERNAME",
        "WORDPRESS_APPLICATION_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)

    assert _missing_wordpress_env() == [
        "WORDPRESS_BASE_URL",
        "WORDPRESS_USERNAME",
        "WORDPRESS_APPLICATION_PASSWORD",
    ]


def test_missing_wordpress_env_accepts_complete_configuration(monkeypatch):
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APPLICATION_PASSWORD", "password")

    assert _missing_wordpress_env() == []


def test_draft_contract_accepts_only_draft_status():
    _assert_draft_contract(
        {"wordpress_draft_delivery": {"request_payload": {"status": "draft"}}}
    )


@pytest.mark.parametrize("status", ["publish", "future", "private", None])
def test_draft_contract_rejects_non_draft_status(status):
    with pytest.raises(RuntimeError, match="status.*draft"):
        _assert_draft_contract(
            {"wordpress_draft_delivery": {"request_payload": {"status": status}}}
        )
