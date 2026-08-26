from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.research.content_research_pipeline import run_content_research_to_wordpress_draft

_REQUIRED_WP_ENV = (
    "WORDPRESS_BASE_URL",
    "WORDPRESS_USERNAME",
    "WORDPRESS_APPLICATION_PASSWORD",
)

_GATE_NAMES = (
    "research_sufficiency",
    "article_draft_quality",
    "claim_audit",
    "seo_strategy",
    "seo_validation",
    "editorial_review",
    "publication",
    "publisher",
    "wordpress_draft_delivery",
)


def _missing_wordpress_env() -> list[str]:
    return [name for name in _REQUIRED_WP_ENV if not os.getenv(name)]


def _gate_status(artifact: dict[str, Any] | None) -> str:
    if artifact is None:
        return "MISSING"
    outcome = artifact.get("outcome")
    gate = artifact.get("gate_status")
    lifecycle = artifact.get("lifecycle_stage")
    if outcome:
        return str(outcome)
    if gate:
        return str(gate)
    if lifecycle:
        return str(lifecycle)
    return "present"


def _print_summary(result: dict[str, Any]) -> None:
    print("=== IRL AI CORE PIPELINE ===")
    for name in _GATE_NAMES:
        artifact = result.get(name)
        if artifact is None:
            print(f"{name}: MISSING")
            continue
        print(
            f"{name}: {_gate_status(artifact)}"
            f" | lifecycle={artifact.get('lifecycle_stage')}"
        )


def _assert_draft_contract(result: dict[str, Any]) -> None:
    delivery = result.get("wordpress_draft_delivery")
    if not isinstance(delivery, dict):
        raise RuntimeError("WordPress Draft contract is missing")

    payload = delivery.get("request_payload")
    if not isinstance(payload, dict) or payload.get("status") != "draft":
        raise RuntimeError("SAFETY STOP: WordPress request_payload.status must be 'draft'")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run an IRL AI Core research/content pipeline."
    )
    parser.add_argument("project", help="Existing research project name, e.g. m7-consultant-liability")
    parser.add_argument(
        "--deliver",
        action="store_true",
        help="Perform the verified live WordPress Draft delivery. Never publishes.",
    )
    args = parser.parse_args(argv)

    if args.deliver:
        missing = _missing_wordpress_env()
        if missing:
            parser.error("--deliver requires: " + ", ".join(missing))

    try:
        result = run_content_research_to_wordpress_draft(
            args.project,
            deliver=args.deliver,
        )
        _print_summary(result)

        publication = result.get("publication")
        if publication is not None and publication.get("gate_status") != "allowed":
            print("PIPELINE: BLOCKED at publication gate", file=sys.stderr)
            return 2

        if "wordpress_draft_delivery" in result:
            _assert_draft_contract(result)

        if args.deliver:
            live = result.get("wordpress_draft_delivery_result")
            if not isinstance(live, dict) or live.get("status") != "draft":
                raise RuntimeError("SAFETY STOP: live WordPress response did not confirm status=draft")
            print("LIVE DELIVERY: PASS")
            print(f"post_id={live.get('post_id')}")
            print(f"status={live.get('status')}")
            print(f"edit_url={live.get('edit_url')}")
        else:
            print("DRY RUN: PASS")
            print("No network delivery was performed.")

        return 0
    except Exception as exc:
        print(f"PIPELINE: ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
