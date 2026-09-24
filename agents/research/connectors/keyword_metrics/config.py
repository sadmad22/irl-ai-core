import os


KEYWORD_METRICS_PROVIDER = os.getenv(
    "IRL_KEYWORD_METRICS_PROVIDER",
    "google_ads",
).strip().lower()

if not KEYWORD_METRICS_PROVIDER:
    KEYWORD_METRICS_PROVIDER = "google_ads"
