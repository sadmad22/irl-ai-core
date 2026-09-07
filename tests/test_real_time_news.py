import pytest
from agents.research.real_time_news import build_real_time_news


def base():
    return {
        "article": {"title": "Insurance market update", "content": "Insurance market content."},
        "outline_editor": {"lifecycle_stage": "outline_editor_ready", "brief_id": "b1", "report_id": "r1", "decision_id": "d1", "strategy_id": "s1"},
        "news": {"source": "news_api", "verified": True, "items": [
            {"news_id": "n1", "url": "https://example.com/1", "title": "New insurance rule", "published_at": "2026-09-07T08:00:00Z", "summary": "Original provider summary.", "relevance_score": 0.9, "status": "verified"},
            {"news_id": "n2", "url": "https://example.com/2", "title": "Older item", "published_at": "2026-09-06T08:00:00Z", "summary": "Older summary.", "relevance_score": 0.8, "status": "verified"},
            {"news_id": "n3", "url": "https://example.com/3", "title": "Rejected item", "published_at": "2026-09-07T09:00:00Z", "summary": "Do not use.", "relevance_score": 1.0, "status": "rejected"},
        ]},
        "max_items": 5, "freshness_hours": 24,
    }


def test_valid_selection_and_summary_integrity():
    x = base(); x["news"]["items"][1]["published_at"] = "2026-09-07T07:00:00Z"
    out = build_real_time_news(**x, as_of="2026-09-07T10:00:00Z")
    assert [i["news_id"] for i in out["items"]] == ["n1", "n2"]
    assert out["items"][0]["summary"] == "Original provider summary."


def test_stale_items_are_excluded():
    out = build_real_time_news(**base(), as_of="2026-09-07T10:00:00Z")
    assert [i["news_id"] for i in out["items"]] == ["n1"]


def test_max_items_and_deterministic_order():
    x = base(); x["news"]["items"].append({"news_id":"n4","url":"https://example.com/4","title":"Tie","published_at":"2026-09-07T06:00:00Z","summary":"Tie summary","relevance_score":0.9,"status":"verified"}); x["max_items"] = 2
    out = build_real_time_news(**x, as_of="2026-09-07T10:00:00Z")
    assert [i["news_id"] for i in out["items"]] == ["n1", "n4"]


def test_same_input_same_id():
    x = base(); a = build_real_time_news(**x, as_of="2026-09-07T10:00:00Z"); b = build_real_time_news(**x, as_of="2026-09-07T10:00:00Z")
    assert a["real_time_news_id"] == b["real_time_news_id"]


def test_reordered_provider_items_same_result():
    x = base(); y = base(); y["news"]["items"] = list(reversed(y["news"]["items"]))
    assert build_real_time_news(**x, as_of="2026-09-07T10:00:00Z") == build_real_time_news(**y, as_of="2026-09-07T10:00:00Z")


@pytest.mark.parametrize("field,value", [("max_items",0),("max_items",21),("freshness_hours",0),("freshness_hours",169)])
def test_bounds(field, value):
    x = base(); x[field] = value
    with pytest.raises(ValueError): build_real_time_news(**x, as_of="2026-09-07T10:00:00Z")


def test_requires_upstream_lifecycle():
    x = base(); x["outline_editor"]["lifecycle_stage"] = "draft"
    with pytest.raises(ValueError): build_real_time_news(**x, as_of="2026-09-07T10:00:00Z")


def test_requires_verified_news_api():
    x = base(); x["news"]["source"] = "search"
    with pytest.raises(ValueError): build_real_time_news(**x, as_of="2026-09-07T10:00:00Z")


def test_requires_as_of_and_valid_timestamps():
    x = base()
    with pytest.raises(ValueError): build_real_time_news(**x, as_of="not-a-date")


def test_rejects_http_url():
    x = base(); x["news"]["items"][0]["url"] = "http://example.com/1"
    with pytest.raises(ValueError): build_real_time_news(**x, as_of="2026-09-07T10:00:00Z")


def test_rejects_duplicate_news_id():
    x = base(); x["news"]["items"][1]["news_id"] = "n1"
    with pytest.raises(ValueError): build_real_time_news(**x, as_of="2026-09-07T10:00:00Z")


def test_rejects_invalid_relevance():
    x = base(); x["news"]["items"][0]["relevance_score"] = 1.1
    with pytest.raises(ValueError): build_real_time_news(**x, as_of="2026-09-07T10:00:00Z")


def test_rejects_missing_item_field():
    x = base(); del x["news"]["items"][0]["summary"]
    with pytest.raises(ValueError): build_real_time_news(**x, as_of="2026-09-07T10:00:00Z")
