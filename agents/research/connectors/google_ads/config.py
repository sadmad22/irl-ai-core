"""Vendor-specific configuration for the Google Ads keyword metrics provider."""

import os


GOOGLE_ADS_BASE_URL = os.getenv(
    "GOOGLE_ADS_BASE_URL",
    "https://googleads.googleapis.com",
).rstrip("/")

GOOGLE_ADS_API_VERSION = os.getenv("GOOGLE_ADS_API_VERSION", "v25").strip().lower()
GOOGLE_ADS_TOKEN_URL = os.getenv(
    "GOOGLE_ADS_TOKEN_URL",
    "https://oauth2.googleapis.com/token",
).strip()

GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
GOOGLE_ADS_CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID")
GOOGLE_ADS_CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
GOOGLE_ADS_REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")

GOOGLE_ADS_CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
GOOGLE_ADS_LOGIN_CUSTOMER_ID = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")

GOOGLE_ADS_TIMEOUT_SECONDS = int(os.getenv("GOOGLE_ADS_TIMEOUT_SECONDS", "20"))
GOOGLE_ADS_MAX_KEYWORDS_PER_REQUEST = int(
    os.getenv("GOOGLE_ADS_MAX_KEYWORDS_PER_REQUEST", "10000")
)

# Application-level mappings. These are intentionally explicit and small:
# unsupported locations/languages must fail closed rather than guess.
GOOGLE_ADS_LOCATION_IDS = {
    "US": "2840",
}

GOOGLE_ADS_LANGUAGE_IDS = {
    "en": "1000",
}
