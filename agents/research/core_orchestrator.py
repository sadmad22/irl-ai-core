from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from .content_research_pipeline import (
    _load,
    run_content_research_to_wordpress_draft,
)
from .wordpress_draft_delivery_client import WordPressConnection

SCHEMA_VERSION = "1.0"
METHOD_VERSION = "v1"
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "shared" / "schemas" / "core-orchestration.schema.json"


def _orchestration_id(project_name: str, state: dict[str, Any]) -> str:
    raw = json.dumps({"project_name": project_name, "state": state}, sort_keys=True, ensure_ascii=False)
    return f"core_orchestration_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _decision_action(*, result: dict[str, Any], decision: dict[str, Any]) -> tuple[str, str]:
    if decision.get("outcome") != "approved":
        return "stop", "Decision Engine did not approve content production."

    quality = result.get("article_draft_quality", {})
    if quality.get("outcome") != "passed":
        return "revise_article_draft", "Article Draft Quality Gate requires revision."

    claim_audit = result.get("claim_audit", {})
    if claim_audit.get("outcome") != "passed":
        return "revise_claims", "Claim Audit requires revision before downstream processing."

    seo = result.get("seo_validation", {})
    if seo.get("outcome") != "passed":
        return "revise_seo", "SEO Validation requires revision."

    editorial = result.get("editorial_review", {})
    if editorial.get("outcome") != "approved":
        return "revise_editorial", "Editorial Review did not approve the draft."

    publication = result.get("publication", {})
    if publication.get("gate_status") != "allowed":
        return "stop", "Publication Gate blocked delivery."

    if "wordpress_draft_delivery_result" in result:
        delivery = result["wordpress_draft_delivery_result"]
        if delivery.get("remote_status") == "draft":
            return "complete", "WordPress draft delivered successfully."

    return "deliver_wordpress_draft", "Content is approved and ready for WordPress draft delivery."


def build_orchestration_result(
    *,
    project_name: str,
    result: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Convert pipeline state into one explicit orchestration decision.

    This function is pure: it does not run agents, write files, or perform
    network I/O. The orchestrator is responsible for choosing the next safe
    action from the existing gate contracts rather than duplicating them.
    """
    next_action, rationale = _decision_action(result=result, decision=decision)

    gates = {
        "article_draft_quality": result.get("article_draft_quality", {}).get("outcome"),
        "claim_audit": result.get("claim_audit", {}).get("outcome"),
        "seo_validation": result.get("seo_validation", {}).get("outcome"),
        "editorial_review": result.get("editorial_review", {}).get("outcome"),
        "publication": result.get("publication", {}).get("gate_status"),
        "wordpress_delivery": result.get("wordpress_draft_delivery_result", {}).get("remote_status"),
    }

    if next_action == "complete":
        lifecycle_stage = "completed"
    elif next_action == "stop":
        lifecycle_stage = "blocked"
    else:
        lifecycle_stage = "action_required"

    state = {
        "lifecycle_stage": lifecycle_stage,
        "next_action": next_action,
        "gates": gates,
        "decision_outcome": decision.get("outcome"),
    }

    return {
        "orchestration_id": _orchestration_id(project_name, state),
        "project_name": project_name,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_stage": lifecycle_stage,
        "current_stage": next_action,
        "next_action": next_action,
        "decision_outcome": decision.get("outcome"),
        "rationale": [rationale],
        "gates": gates,
        "audit": {
            "method": "irl_core_decision_orchestrator",
            "version": METHOD_VERSION,
            "validation_status": "validated",
        },
    }


def run_irl_core(
    project_name: str,
    *,
    deliver: bool = False,
    connection: WordPressConnection | None = None,
    transport: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run the complete IRL Core and expose one authoritative orchestration state."""
    result = run_content_research_to_wordpress_draft(
        project_name,
        deliver=deliver,
        connection=connection,
        transport=transport,
    )
    decision = _load(project_name, "decision.json")
    orchestration = build_orchestration_result(
        project_name=project_name,
        result=result,
        decision=decision,
    )
    result["core_orchestration"] = orchestration
    return result
