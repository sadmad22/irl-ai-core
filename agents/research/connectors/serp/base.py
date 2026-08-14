from abc import ABC, abstractmethod


class SERPProvider(ABC):
    """
    Base interface for SERP providers.
    """

    @abstractmethod
    def get_results(
        self,
        keyword: str,
        language: str,
        country: str,
    ) -> dict:
        """
        Return SERP analysis.
        """
        raise NotImplementedError