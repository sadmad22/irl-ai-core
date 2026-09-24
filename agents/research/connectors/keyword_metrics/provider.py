from .base import KeywordMetricsProvider
from .config import KEYWORD_METRICS_PROVIDER
from .providers.dataforseo import DataForSEOKeywordMetricsProvider
from .providers.mock import MockKeywordMetricsProvider


PROVIDER_CLASSES = {
    "dataforseo": DataForSEOKeywordMetricsProvider,
    "mock": MockKeywordMetricsProvider,
}


def get_provider(provider_name: str | None = None) -> KeywordMetricsProvider:
    """Return the configured or explicitly requested keyword metrics provider."""
    selected = (provider_name or KEYWORD_METRICS_PROVIDER).strip().lower()
    provider_class = PROVIDER_CLASSES.get(selected)
    if provider_class is None:
        supported = ", ".join(sorted(PROVIDER_CLASSES))
        raise ValueError(
            "Unsupported keyword metrics provider: "
            f"{selected}. Supported providers: {supported}"
        )
    return provider_class()


def get_capabilities(provider_name: str | None = None) -> frozenset[str]:
    """Return declared capabilities without making a network call."""
    return get_provider(provider_name).get_capabilities()
