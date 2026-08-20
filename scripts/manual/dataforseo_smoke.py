from agents.research.connectors.keyword_metrics.provider import get_provider

provider = get_provider()

result = provider.get_metrics(
    keyword="expat health insurance",
    language="en",
    country="US",
)

print(result)