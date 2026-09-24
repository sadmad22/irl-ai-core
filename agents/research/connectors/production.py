"""Production-only provider policy.

Production must use the real providers selected by the DataForSEO replacement:
- Brave for SERP/Search
- Google Ads for Keyword Metrics

Legacy DataForSEO and Mock implementations remain available for tests,
migration compatibility, and non-production explicit use.
"""

import os

from .errors import ProviderConfigurationError

PRODUCTION_ENVIRONMENT = "production"

SERP_PRODUCTION_PROVIDER = "brave"
KEYWORD_METRICS_PRODUCTION_PROVIDER = "google_ads"


def is_production_environment() -> bool:
    value = os.getenv("IRL_ENVIRONMENT", "development").strip().lower()
    return value == PRODUCTION_ENVIRONMENT


def require_production_provider(
    *,
    capability: str,
    provider: str,
    expected_provider: str,
) -> None:
    """Reject legacy/non-production providers when IRL_ENVIRONMENT=production."""
    if not is_production_environment():
        return

    if provider != expected_provider:
        raise ProviderConfigurationError(
            f"Production {capability} provider must be {expected_provider}; "
            f"got {provider}. No DataForSEO or Mock fallback is allowed.",
            provider=provider,
        )
