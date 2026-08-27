from scripts.web_ui import PROJECT_RE, gate_status, public_result


def test_project_name_contract():
    assert PROJECT_RE.fullmatch("expat-health-insurance")
    assert PROJECT_RE.fullmatch("nurse-insurance-2026")
    assert not PROJECT_RE.fullmatch("Expat Health Insurance")
    assert not PROJECT_RE.fullmatch("x")


def test_gate_status_precedence():
    assert gate_status({"outcome": "passed", "lifecycle_stage": "ready"}) == "passed"
    assert gate_status({"gate_status": "allowed", "lifecycle_stage": "ready"}) == "allowed"
    assert gate_status({"lifecycle_stage": "publisher_ready"}) == "publisher_ready"
    assert gate_status(None) == "pending"


def test_public_result_contains_only_operator_safe_live_fields():
    result = public_result(
        {
            "claim_audit": {"outcome": "passed"},
            "publication": {"gate_status": "allowed"},
            "wordpress_draft_delivery_result": {
                "post_id": 4949,
                "status": "draft",
                "edit_url": "https://example.test/?p=4949",
                "request_payload": {"content": "secret", "status": "draft"},
            },
        }
    )
    assert result["gates"]["claim_audit"] == "passed"
    assert result["gates"]["publication"] == "allowed"
    assert result["live"] == {
        "post_id": 4949,
        "status": "draft",
        "edit_url": "https://example.test/?p=4949",
    }
    assert "request_payload" not in result["live"]
