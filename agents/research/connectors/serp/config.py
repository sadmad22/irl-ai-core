import os


SERP_PROVIDER = os.getenv("IRL_SERP_PROVIDER", "dataforseo").strip().lower()

if not SERP_PROVIDER:
    SERP_PROVIDER = "dataforseo"
