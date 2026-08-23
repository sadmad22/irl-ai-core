"""Verification contract for autonomous recovery executions.

The executor mutates an artifact; this module verifies the gates explicitly
listed by the recovery plan after the pipeline is re-run.
"""

from __future__ import annotations

from typing import Any, Mapping


class RecoveryVerificationError(RuntimeError):
    """Raised when a recovery result cannot satisfy its verification contract."""


_SUCCESS_OUTCOMES = {"passed", "approved", "allowed", "supported"}


def _gate_outcome(result: Mapping[str, Any], gate: str) -> str:
    gate_result = result.get(gate)
    if not isinstance(gate_result, Mapping):
        return ""
    return str(gate_result.get("outcome") or gate_result.get("gate_status") or "").strip().lower()


def verify_recovery(*, plan: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    """Verify every gate explicitly requested by a recovery plan.

    Verification is intentionally small: a gate must exist and report one of
    the accepted successful outcomes. Missing or failed gates are failures.
    """
    strategy = str(plan.get("strategy", "")).strip()
    recovery_id = str(plan.get("recovery_id", "")).strip()
    rerun_gates = plan.get("rerun_gates", [])
    if not strategy:
        raise RecoveryVerificationError("recovery plan is missing a strategy")
    if not isinstance(rerun_gates, list) or not rerun_gates:
        raise RecoveryVerificationError(f"recovery plan has no verification gates: {strategy}")

    checks: list[dict[str, Any]] = []
    failed: list[str] = []
    for gate in rerun_gates:
        gate_name = str(gate).strip()
        if not gate_name:
            raise RecoveryVerificationError(f"recovery plan contains an empty verification gate: {strategy}")
        outcome = _gate_outcome(result, gate_name)
        passed = outcome in _SUCCESS_OUTCOMES
        checks.append({"gate": gate_name, "outcome": outcome, "passed": passed})
        if not passed:
            failed.append(gate_name)

    return {
        "recovery_id": recovery_id,
        "strategy": strategy,
        "status": "passed" if not failed else "failed",
        "passed": not failed,
        "checks": checks,
        "failed_gates": failed,
    }
