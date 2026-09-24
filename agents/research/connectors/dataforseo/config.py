import os


DATAFORSEO_BASE_URL = os.getenv(
    "DATAFORSEO_BASE_URL",
    "https://api.dataforseo.com",
).rstrip("/")

DATAFORSEO_LOGIN = os.getenv("DATAFORSEO_LOGIN")
DATAFORSEO_PASSWORD = os.getenv("DATAFORSEO_PASSWORD")

DATAFORSEO_LOCATION_CODES = {
    "US": 2840,
}
