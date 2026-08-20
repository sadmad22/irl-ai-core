from agents.research.connectors.keyword_metrics.provider import get_provider

provider = get_provider()

metrics = provider.get_metrics(
    keyword="expat health insurance",
    language="en",
    country="US",
)

print(metrics)