from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "shared" / "schemas" / "production-orchestration.schema.json"

STAGES = [
    "research", "intelligence", "configuration", "structure", "draft",
    "editorial_cleanup", "media", "linking", "optimization", "qa",
    "production_assembly", "article_package", "production_delivery_boundary",
    "wordpress_delivery",
]


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _base(*, lifecycle: str = "running") -> dict:
    return {
        "orchestration_id": "orchestration_0123456789abcdef",
        "project_name": "expat-health-insurance",
        "schema_version": "1.0",
        "lifecycle_stage": lifecycle,
        "current_stage": "production_assembly" if lifecycle in {"running", "failed"} else None,
        "completed_stages": STAGES[:10],
        "remaining_stages": STAGES[10:],
        "lineage": {
            "report_id": "report_123", "decision_id": "decision_123", "strategy_id": "strategy_123",
            "brief_id": "brief_123", "draft_id": "draft_123", "quality_id": "quality_123",
            "optimization_id": "optimization_123",
        },
        "production": {
            "assembly": {"assembly_id": "assembly_0123456789abcdef", "lifecycle_stage": "production_assembly_ready"},
            "package": {"package_id": "package_0123456789abcdef", "lifecycle_stage": "delivery_ready", "validation_status": "validated"},
            "boundary": {"delivery_id": "delivery_0123456789abcdef", "lifecycle_stage": "delivery_ready", "delivery_status": "ready"},
            "wordpress": {"execution_mode": "dry_run", "delivery_status": "ready", "publish": False, "human_approval_required": True},
        },
        "error": None,
        "audit": {"method": "irl_production_orchestrator", "version": "v1", "validation_status": "validated"},
    }


def _errors(value: dict) -> list:
    validator = Draft202012Validator(_schema(), format_checker=FormatChecker())
    return sorted(validator.iter_errors(value), key=lambda error: list(error.path))


def test_running_orchestration_is_valid():
    assert _errors(_base()) == []


def test_completed_non_delivery_orchestration_is_valid():
    value = _base(lifecycle="completed")
    value["completed_stages"] = STAGES[:10]
    value["remaining_stages"] = []
    value["current_stage"] = None
    value["production"]["assembly"]["lifecycle_stage"] = "production_assembly_ready"
    value["production"]["package"]["lifecycle_stage"] = "package_ready"
    value["production"]["boundary"]["lifecycle_stage"] = "delivery_ready"
    value["production"]["wordpress"]["execution_mode"] = "dry_run"
    assert _errors(value) == []


def test_human_review_requires_controlled_wordpress_terminal_state():
    value = _base(lifecycle="human_review")
    value["completed_stages"] = STAGES
    value["remaining_stages"] = []
    value["current_stage"] = None
    value["production"]["package"]["lifecycle_stage"] = "delivery_ready"
    value["production"]["boundary"] = {
        "delivery_id": "delivery_0123456789abcdef",
        "lifecycle_stage": "delivered_as_draft",
        "delivery_status": "delivered",
    }
    value["production"]["wordpress"] = {
        "execution_mode": "live", "delivery_status": "delivered", "platform_post_id": 4957,
        "remote_status": "draft", "edit_url": "https://insurancereviewlab.com/wp-admin/post.php?post=4957&action=edit",
        "publish": False, "human_approval_required": True,
    }
    assert _errors(value) == []


def test_failed_orchestration_requires_error_and_failed_audit():
    value = _base(lifecycle="failed")
    value["remaining_stages"] = STAGES[11:]
    value["completed_stages"] = STAGES[:11]
    value["error"] = {"stage": "article_package", "type": "PackageValidationError", "message": "Article Package validation failed."}
    value["audit"]["validation_status"] = "failed"
    assert _errors(value) == []


def test_unknown_stage_is_rejected():
    value = _base()
    value["current_stage"] = "not_a_stage"
    assert _errors(value)


def test_duplicate_stage_checkpoint_is_rejected():
    value = _base()
    value["completed_stages"].append("qa")
    assert _errors(value)


def test_lineage_required_fields_are_enforced():
    value = _base()
    del value["lineage"]["draft_id"]
    assert _errors(value)


def test_publish_true_is_rejected():
    value = _base()
    value["production"]["wordpress"]["publish"] = True
    assert _errors(value)


def test_human_review_cannot_have_remaining_stages():
    value = _base(lifecycle="human_review")
    value["completed_stages"] = STAGES
    value["current_stage"] = None
    value["remaining_stages"] = ["wordpress_delivery"]
    value["production"]["boundary"]["lifecycle_stage"] = "delivered_as_draft"
    value["production"]["boundary"]["delivery_status"] = "delivered"
    value["production"]["wordpress"] = {
        "execution_mode": "live", "delivery_status": "delivered", "remote_status": "draft",
        "publish": False, "human_approval_required": True,
    }
    assert _errors(value)


def test_completed_cannot_have_current_stage():
    value = _base(lifecycle="completed")
    value["remaining_stages"] = []
    value["current_stage"] = "qa"
    assert _errors(value)


def test_running_cannot_have_error():
    value = _base()
    value["error"] = {"stage": "qa", "type": "QualityGateBlocked", "message": "Quality gate failed."}
    assert _errors(value)


def test_unknown_top_level_fields_are_rejected():
    value = _base()
    value["unexpected"] = True
    assert _errors(value)


def test_schema_validation_does_not_mutate_fixture():
    value = _base()
    original = copy.deepcopy(value)
    _errors(value)
    assert value == original
