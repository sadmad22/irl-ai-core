from abc import ABC, abstractmethod


class KeywordMetricsProvider(ABC):
    """
    Base interface for keyword metrics providers.
    """

    @abstractmethod
    def get_metrics(
        self,
        keyword: str,
        language: str,
        country: str,
    ) -> dict:
        """
        Return keyword metrics.
        """
        raise NotImplementedError