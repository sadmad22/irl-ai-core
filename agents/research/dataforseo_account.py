from __future__ import annotations

import base64
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://api.dataforseo.com"


def _credentials() -> tuple[str, str, str]:
    base_url = os.getenv("DATAFORSEO_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    login = os.getenv("DATAFORSEO_LOGIN", "").strip()
    password = os.getenv("DATAFORSEO_PASSWORD", "").strip()
    return base_url, login, password


def _find_first(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = _find_first(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_first(child, key)
            if found is not None:
                return found
    return None


def _walk_pricing(value: Any, path: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if "cost_type" in value and "cost" in value:
            rows.append({"path": ".".join(path), "cost_type": value.get("cost_type"), "cost": value.get("cost")})
        for key, child in value.items():
            rows.extend(_walk_pricing(child, path + (str(key),)))
    elif isinstance(value, list):
        for child in value:
            rows.extend(_walk_pricing(child, path))
    return rows


def _extract_result(payload: dict[str, Any]) -> dict[str, Any]:
    tasks = payload.get("tasks") or []
    if not tasks:
        raise RuntimeError(payload.get("status_message") or "DataForSEO returned no account data")
    task = tasks[0]
    if int(task.get("status_code", 0) or 0) >= 40000:
        raise RuntimeError(task.get("status_message") or "DataForSEO account request failed")
    results = task.get("result") or []
    if not results:
        raise RuntimeError("DataForSEO returned an empty account result")
    return results[0]


def fetch_account() -> dict[str, Any]:
    base_url, login, password = _credentials()
    if not login or not password:
        return {"configured": False, "error": "DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD are required"}

    token = base64.b64encode(f"{login}:{password}".encode("utf-8")).decode("ascii")
    request = Request(
        f"{base_url}/v3/appendix/user_data",
        headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return {"configured": True, "error": f"DataForSEO HTTP {exc.code}"}
    except (URLError, TimeoutError, ValueError) as exc:
        return {"configured": True, "error": f"DataForSEO request failed: {exc}"}

    try:
        result = _extract_result(payload)
    except RuntimeError as exc:
        return {"configured": True, "error": str(exc)}

    rates = result.get("rates") if isinstance(result.get("rates"), dict) else result
    money = _find_first(rates, "money") or {}
    price = _find_first(rates, "price") or {}
    balance = money.get("balance") if isinstance(money, dict) else None
    total = money.get("total") if isinstance(money, dict) else None
    pricing = _walk_pricing(price)

    return {
        "configured": True,
        "login": result.get("login"),
        "timezone": result.get("timezone"),
        "balance": balance,
        "total_deposited": total,
        "pricing": pricing,
        "backlinks_subscription_expiry_date": result.get("backlinks_subscription_expiry_date"),
        "llm_mentions_subscription_expiry_date": result.get("llm_mentions_subscription_expiry_date"),
    }


def pricing_summary(account: dict[str, Any], limit: int = 30) -> list[dict[str, Any]]:
    rows = account.get("pricing") if isinstance(account, dict) else []
    if not isinstance(rows, list):
        return []
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        path = str(row.get("path", ""))
        parts = path.split(".")
        api = parts[0] if parts else "unknown"
        function = parts[-2] if len(parts) >= 2 else "unknown"
        cost_type = str(row.get("cost_type", ""))
        cost = row.get("cost")
        key = (api, function, f"{cost_type}:{cost}")
        if key in seen:
            continue
        seen.add(key)
        output.append({"api": api, "function": function, "cost_type": cost_type, "cost": cost})
        if len(output) >= limit:
            break
    return output
