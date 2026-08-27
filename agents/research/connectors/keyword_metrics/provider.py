from .base import KeywordMetricsProvider
from .providers.mock import MockKeywordMetricsProvider
from .providers.dataforseo import DataForSEOKeywordMetricsProvider
from .config import ACTIVE_PROVIDER


def get_provider(provider: str | None = None) -> KeywordMetricsProvider:
    """Return the requested keyword metrics provider."""
    selected = (provider or ACTIVE_PROVIDER).strip().lower()
    if selected == "dataforseo":
        return DataForSEOKeywordMetricsProvider()
    if selected == "mock":
        return MockKeywordMetricsProvider()
    raise ValueError(f"Unsupported keyword metrics provider: {selected}")
