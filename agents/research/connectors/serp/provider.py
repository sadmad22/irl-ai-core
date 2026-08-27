from .providers.dataforseo import DataForSEOSERPProvider
from .base import SERPProvider
from .providers.mock import MockSERPProvider
from .config import ACTIVE_PROVIDER


def get_provider(provider: str | None = None) -> SERPProvider:
    """Return the requested SERP provider."""
    selected = (provider or ACTIVE_PROVIDER).strip().lower()
    if selected == "dataforseo":
        return DataForSEOSERPProvider()
    if selected == "mock":
        return MockSERPProvider()
    raise ValueError(f"Unsupported SERP provider: {selected}")
