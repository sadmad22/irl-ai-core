from .providers.dataforseo import DataForSEOSERPProvider
from .base import SERPProvider
from .providers.mock import MockSERPProvider
from .config import ACTIVE_PROVIDER


def get_provider() -> SERPProvider:
    """
    Return the active SERP provider.
    """

    if ACTIVE_PROVIDER == "dataforseo":
        return DataForSEOSERPProvider()

    if ACTIVE_PROVIDER == "mock":
        return MockSERPProvider()

    raise ValueError(f"Unsupported provider: {ACTIVE_PROVIDER}")