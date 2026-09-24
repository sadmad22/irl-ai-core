from .base import SERPProvider
from .config import SERP_PROVIDER
from .providers.brave import BraveSERPProvider
from .providers.dataforseo import DataForSEOSERPProvider
from .providers.mock import MockSERPProvider


PROVIDER_CLASSES = {
    "brave": BraveSERPProvider,
    "dataforseo": DataForSEOSERPProvider,
    "mock": MockSERPProvider,
}


def get_provider(provider_name: str | None = None) -> SERPProvider:
    """Return the configured or explicitly requested SERP provider."""
    selected = (provider_name or SERP_PROVIDER).strip().lower()
    provider_class = PROVIDER_CLASSES.get(selected)
    if provider_class is None:
        supported = ", ".join(sorted(PROVIDER_CLASSES))
        raise ValueError(
            f"Unsupported SERP provider: {selected}. Supported providers: {supported}"
        )
    return provider_class()


def get_capabilities(provider_name: str | None = None) -> frozenset[str]:
    """Return declared capabilities without making a network call."""
    return get_provider(provider_name).get_capabilities()