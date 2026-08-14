import os

ACTIVE_PROVIDER = "dataforseo"

USE_MOCK = True

BASE_URL = "https://api.dataforseo.com"

API_KEY = None

LOGIN = os.getenv("DATAFORSEO_LOGIN")
PASSWORD = os.getenv("DATAFORSEO_PASSWORD")

LOCATION_CODES = {
    "US": 2840,
}