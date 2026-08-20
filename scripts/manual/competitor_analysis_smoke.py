from agents.research.analyzers.competitor import analyze_competitors
from agents.research.agent import load_project_file


serp_data = load_project_file(
    "expat-health-insurance",
    "serp-analysis.json",
)

result = analyze_competitors(serp_data)

print(result)