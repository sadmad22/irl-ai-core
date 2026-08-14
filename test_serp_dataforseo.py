from agents.research.connectors.serp.providers.dataforseo import (
    DataForSEOSERPProvider,
)

provider = DataForSEOSERPProvider()

result = provider.get_results(
    keyword="expat health insurance",
    language="en",
    country="US",
)

print(result)