from abc import ABC, abstractmethod
from typing import Any


SERP_CAPABILITIES = frozenset(
    {
        "result_title",
        "result_url",
        "result_domain",
        "result_snippet",
        "provider_order",
    }
)


def validate_serp_response(
    payload: dict[str, Any],
    *,
    expected_provider: str | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("SERP provider must return an object")

    required = {
        "provider",
        "keyword",
        "language",
        "country",
        "position_semantics",
        "results",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"SERP provider response missing fields: {', '.join(missing)}")

    provider = payload["provider"]
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("SERP provider response provider must be a non-empty string")
    if expected_provider and provider != expected_provider:
        raise ValueError(
            f"SERP provider provenance mismatch: expected {expected_provider}, got {provider}"
        )

    for field in ("keyword", "language", "country"):
        value = payload[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"SERP provider response {field} must be a non-empty string")

    if payload["position_semantics"] != "provider_order":
        raise ValueError("SERP position semantics must be provider_order")

    results = payload["results"]
    if not isinstance(results, list):
        raise ValueError("SERP provider results must be an array")

    for index, result in enumerate(results, start=1):
        if not isinstance(result, dict):
            raise ValueError(f"SERP result {index} must be an object")
        required_result = {"position", "title", "url", "domain", "snippet"}
        missing_result = sorted(required_result - result.keys())
        if missing_result:
            raise ValueError(
                f"SERP result {index} missing fields: {', '.join(missing_result)}"
            )
        if result["position"] != index:
            raise ValueError(
                f"SERP result {index} position must equal provider order {index}"
            )
        for field in ("title", "url", "domain", "snippet"):
            if not isinstance(result[field], str):
                raise ValueError(f"SERP result {index} {field} must be a string")

    return payload


class SERPProvider(ABC):
    """Stable capability boundary for SERP/search providers."""

    provider_name = "unknown"
    capabilities = SERP_CAPABILITIES

    def get_capabilities(self) -> frozenset[str]:
        return frozenset(self.capabilities)

    @abstractmethod
    def get_results(
        self,
        keyword: str,
        language: str,
        country: str,
    ) -> dict:
        """Return a normalized SERP provider response."""
        raise NotImplementedError
