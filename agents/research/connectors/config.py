import os

from agents.research.provider_config import load_saved_environment

load_saved_environment()

ACTIVE_PROVIDER = os.getenv("IRL_RESEARCH_PROVIDER", "dataforseo").strip().lower() or "dataforseo"

BASE_URL = os.getenv("DATAFORSEO_BASE_URL", "https://api.dataforseo.com").strip().rstrip("/")

LOGIN = os.getenv("DATAFORSEO_LOGIN")
PASSWORD = os.getenv("DATAFORSEO_PASSWORD")

LOCATION_CODES = {
    "US": 2840,
}
