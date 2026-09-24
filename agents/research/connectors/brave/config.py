"""Vendor-specific configuration for the Brave Search SERP provider."""

import os


BRAVE_SEARCH_BASE_URL = os.getenv(
    "BRAVE_SEARCH_BASE_URL",
    "https://api.search.brave.com/res/v1/web/search",
).rstrip("/")

BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")

BRAVE_SEARCH_COUNT = int(os.getenv("BRAVE_SEARCH_COUNT", "20"))
BRAVE_SEARCH_OFFSET = int(os.getenv("BRAVE_SEARCH_OFFSET", "0"))
BRAVE_SEARCH_FRESHNESS = os.getenv("BRAVE_SEARCH_FRESHNESS", "").strip()
BRAVE_SEARCH_TIMEOUT_SECONDS = int(os.getenv("BRAVE_SEARCH_TIMEOUT_SECONDS", "15"))
