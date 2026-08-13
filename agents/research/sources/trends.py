from urllib.parse import quote


def build_trends_url(keyword: str, country: str = "US") -> str:
    """
    Build a Google Trends Explore URL for a keyword and country.
    """

    encoded_keyword = quote(keyword)

    return (
        "https://trends.google.com/trends/explore"
        f"?q={encoded_keyword}"
        f"&geo={country}"
    )


if __name__ == "__main__":

    url = build_trends_url(
        "expat health insurance",
        "US"
    )

    print(url)