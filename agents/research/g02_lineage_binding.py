from __future__ import annotations

from typing import Any


OPTIMIZATION_LINEAGE_KEYS = ("report_id", "decision_id", "strategy_id", "brief_id")


def validate_optimization_lineage(artifacts: dict[str, Any], canonical_lineage: dict[str, Any]) -> str:
    optimization = artifacts.get("optimization")
    if not isinstance(optimization, dict):
        raise ValueError("LINEAGE_MISMATCH: optimization artifact is missing")

    optimization_id = optimization.get("optimization_id")
    lineage = optimization.get("lineage")
    if not isinstance(optimization_id, str) or not optimization_id:
        raise ValueError("LINEAGE_MISMATCH: optimization_id is missing")
    if not isinstance(lineage, dict):
        raise ValueError("LINEAGE_MISMATCH: optimization lineage is missing")

    for key in OPTIMIZATION_LINEAGE_KEYS:
        if lineage.get(key) != canonical_lineage.get(key):
            raise ValueError(f"LINEAGE_MISMATCH: optimization {key} conflicts with canonical lineage")

    return optimization_id
