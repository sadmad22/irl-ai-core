from abc import ABC, abstractmethod
from typing import Any


KEYWORD_METRICS_CAPABILITIES = frozenset(
    {
        "search_volume",
        "competition",
        "cpc",
        "historical_trend",
    }
)


def validate_keyword_metrics_response(
    payload: dict[str, Any],
    *,
    expected_provider: str | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("Keyword metrics provider must return an object")

    required = {
        "provider",
        "keyword",
        "search_volume",
        "competition",
        "cpc",
        "trend",
        "language",
        "country",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(
            "Keyword metrics provider response missing fields: "
            + ", ".join(missing)
        )

    provider = payload["provider"]
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("Keyword metrics provider must identify its provider")
    if expected_provider and provider != expected_provider:
        raise ValueError(
            f"Keyword metrics provenance mismatch: expected {expected_provider}, got {provider}"
        )

    if not isinstance(payload["keyword"], str) or not payload["keyword"].strip():
        raise ValueError("Keyword metrics keyword must be a non-empty string")
    if not isinstance(payload["search_volume"], (int, float)) or payload["search_volume"] < 0:
        raise ValueError("Keyword metrics search_volume must be non-negative")
    if (
        not isinstance(payload["competition"], (int, float))
        or not 0 <= payload["competition"] <= 100
    ):
        raise ValueError("Keyword metrics competition must be between 0 and 100")
    if not isinstance(payload["cpc"], (int, float)) or payload["cpc"] < 0:
        raise ValueError("Keyword metrics cpc must be non-negative")
    if not isinstance(payload["trend"], list):
        raise ValueError("Keyword metrics trend must be an array")

    for field in ("language", "country"):
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise ValueError(f"Keyword metrics {field} must be a non-empty string")

    return payload


class KeywordMetricsProvider(ABC):
    """Stable capability boundary for keyword metrics providers."""

    provider_name = "unknown"
    capabilities = KEYWORD_METRICS_CAPABILITIES

    def get_capabilities(self) -> frozenset[str]:
        return frozenset(self.capabilities)

    @abstractmethod
    def get_metrics(
        self,
        keyword: str,
        language: str,
        country: str,
    ) -> dict:
        """Return a normalized keyword metrics provider response."""
        raise NotImplementedError
