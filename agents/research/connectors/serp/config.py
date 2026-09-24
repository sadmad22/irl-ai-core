import os


SERP_PROVIDER = os.getenv("IRL_SERP_PROVIDER", "brave").strip().lower()

if not SERP_PROVIDER:
    SERP_PROVIDER = "brave"
