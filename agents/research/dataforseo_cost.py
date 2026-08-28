from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dataforseo_account import fetch_account

COST_FILE = "dataforseo-cost.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def snapshot() -> dict[str, Any]:
    account = fetch_account()
    if not account.get("configured") or account.get("error"):
        return {
            "available": False,
            "balance": None,
            "captured_at": _now(),
            "error": account.get("error") or "DataForSEO account unavailable",
        }
    try:
        balance = float(account.get("balance"))
    except (TypeError, ValueError):
        return {"available": False, "balance": None, "captured_at": _now(), "error": "DataForSEO balance is unavailable"}
    return {"available": True, "balance": balance, "captured_at": _now()}


def start_run(provider: str | None) -> dict[str, Any]:
    if (provider or "").strip().lower() != "dataforseo":
        return {"provider": provider, "available": False, "balance": None, "captured_at": _now(), "reason": "Exact DataForSEO cost applies only to the DataForSEO provider."}
    return {"provider": "dataforseo", **snapshot()}


def finish_run(project: str, start: dict[str, Any], provider: str | None) -> dict[str, Any]:
    end = start_run(provider) if (provider or "").strip().lower() == "dataforseo" else {"provider": provider, "available": False, "balance": None, "captured_at": _now(), "reason": "Exact DataForSEO cost applies only to the DataForSEO provider."}
    result: dict[str, Any] = {
        "version": "1.0",
        "project": project,
        "provider": provider,
        "measurement": "account_balance_delta",
        "started_at": start.get("captured_at"),
        "finished_at": end.get("captured_at"),
        "start_balance": start.get("balance"),
        "end_balance": end.get("balance"),
        "exact": False,
        "cost": None,
        "currency": "USD",
        "error": None,
    }
    if start.get("available") and end.get("available"):
        delta = round(float(start["balance"]) - float(end["balance"]), 6)
        if delta >= 0:
            result["cost"] = delta
            result["exact"] = True
        else:
            result["error"] = "Account balance increased during the run; cost cannot be isolated safely."
    else:
        result["error"] = end.get("error") or start.get("error") or "Account balance snapshots unavailable."
    path = Path("research") / project / COST_FILE
    path.write_text(json.dumps(result, indent=4, ensure_ascii=False), encoding="utf-8")
    return result


def load_project_cost(project: str) -> dict[str, Any]:
    path = Path("research") / project / COST_FILE
    if not path.exists():
        return {"exact": False, "cost": None, "provider": None, "error": "No per-project cost record."}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"exact": False, "cost": None, "provider": None, "error": "Invalid per-project cost record."}
