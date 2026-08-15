from collections import Counter
from urllib.parse import urlparse


def analyze_competitors(serp_data: dict) -> dict:
    """
    Analyze competitors from normalized SERP data.
    """

    competitors = []

    for result in serp_data.get("results", []):
        url = result.get("url", "")

        domain = result.get("domain")

        if not domain and url:
            domain = urlparse(url).netloc

        competitors.append(
            {
                "position": result.get("position"),
                "domain": domain,
                "title": result.get("title"),
                "url": url,
            }
        )

    domain_counts = Counter(
        competitor["domain"]
        for competitor in competitors
        if competitor["domain"]
    )

    positions = [
    competitor["position"]
    for competitor in competitors
    if isinstance(competitor["position"], int)
]

    average_position = (
    sum(positions) / len(positions)
    if positions
    else None
)

    return {
    "keyword": serp_data.get("keyword", ""),
    "country": serp_data.get("country", ""),
    "language": serp_data.get("language", ""),
    "competitors": competitors,
    "domain_counts": dict(domain_counts),
    "average_position": average_position,
    "top_competitors": competitors[:5],
}