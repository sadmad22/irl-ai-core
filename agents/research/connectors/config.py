import os


ACTIVE_PROVIDER = "dataforseo"

BASE_URL = "https://api.dataforseo.com"

LOGIN = os.getenv("DATAFORSEO_LOGIN")
PASSWORD = os.getenv("DATAFORSEO_PASSWORD")

LOCATION_CODES = {
    "US": 2840,
}