class ProviderError(RuntimeError):
    """Base error for all external provider boundary failures."""

    code = "provider_error"

    def __init__(self, message: str, *, provider: str | None = None, cause: Exception | None = None):
        super().__init__(message)
        self.provider = provider
        self.cause = cause


class ProviderConfigurationError(ProviderError):
    code = "configuration_error"


class ProviderAuthenticationError(ProviderError):
    code = "authentication_error"


class ProviderRateLimitError(ProviderError):
    code = "rate_limit_error"


class ProviderNetworkError(ProviderError):
    code = "network_error"


class ProviderResponseError(ProviderError):
    code = "response_error"


class ProviderCapabilityError(ProviderError):
    code = "capability_error"
