from .base import KeywordMetricsProvider
from .providers.mock import MockKeywordMetricsProvider
from .providers.dataforseo import DataForSEOKeywordMetricsProvider

# Active provider
from .config import ACTIVE_PROVIDER


def get_provider() -> KeywordMetricsProvider:
    """
    Return the active keyword metrics provider.
    """

    if ACTIVE_PROVIDER == "dataforseo":
        return DataForSEOKeywordMetricsProvider()

    return MockKeywordMetricsProvider()