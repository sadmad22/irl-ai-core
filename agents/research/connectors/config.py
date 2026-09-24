"""Capability-neutral connector configuration helpers.

Vendor credentials and provider selection belong to capability-specific
configuration modules. This module intentionally contains no provider-specific
settings.
"""

import os


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip() or default
