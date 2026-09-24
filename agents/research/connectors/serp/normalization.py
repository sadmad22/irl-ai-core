from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_QUERY_PARAMS = {
    "gclid",
    "fbclid",
    "dclid",
    "msclkid",
    "srsltid",
    "_gl",
}


def normalize_serp_url(url: str) -> str:
    """Normalize known tracking parameters without changing functional parameters."""
    if not url:
        return url

    parts = urlsplit(url)
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_PARAMS and not key.lower().startswith("utm_")
    ]

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(filtered_query),
            parts.fragment,
        )
    )
