import json
from pathlib import Path

from .connectors.keyword_metrics.provider import get_provider
from .connectors.serp.provider import get_provider as get_serp_provider
from .connectors.serp.providers.dataforseo import normalize_serp_url
from .analyzers.competitor import analyze_competitors
from .analyzers.intent_alignment import analyze_intent_alignment
from .analyzers.serp_strategy_signal import analyze_serp_strategy_signal
from .analyzers.query_intent import classify_query_intent
from .analyzers.serp_intent import analyze_serp_intent
from .evidence.query_intent import build_query_intent_evidence
from .evidence.serp_intent import build_serp_intent_evidence
from .evidence.intent_alignment import build_intent_alignment_evidence
from .evidence.serp_strategy_signal import build_serp_strategy_signal_evidence
from .report import build_research_report

SEARCH_METRICS_FILE = "search-metrics.json"
SERP_ANALYSIS_FILE = "serp-analysis.json"
COMPETITOR_ANALYSIS_FILE = "competitor-analysis.json"
QUERY_INTENT_ANALYSIS_FILE = "query-intent-analysis.json"
QUERY_INTENT_EVIDENCE_FILE = "query-intent-evidence.json"
SERP_INTENT_ANALYSIS_FILE = "serp-intent-analysis.json"
SERP_INTENT_EVIDENCE_FILE = "serp-intent-evidence.json"
INTENT_ALIGNMENT_ANALYSIS_FILE = "intent-alignment-analysis.json"
INTENT_ALIGNMENT_EVIDENCE_FILE = "intent-alignment-evidence.json"
SERP_STRATEGY_SIGNAL_FILE = "serp-strategy-signal.json"
SERP_STRATEGY_SIGNAL_EVIDENCE_FILE = "serp-strategy-signal-evidence.json"
RESEARCH_REPORT_FILE = "research-report.json"


def load_keyword(project_name: str) -> dict:
    file_path = Path("research") / project_name / "keyword.json"
    return json.loads(file_path.read_text(encoding="utf-8"))


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def save_project_file(project_name: str, filename: str, data: dict) -> None:
    save_json(Path("research") / project_name / filename, data)


def load_project_file(project_name: str, filename: str) -> dict:
    path = Path("research") / project_name / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_project_file_if_changed(project_name: str, filename: str, data: dict) -> None:
    current_data = load_project_file(project_name, filename)
    if current_data != data:
        save_project_file(project_name, filename, data)


def canonicalize_serp_results(serp_data: dict) -> dict:
    data = dict(serp_data)
    data["results"] = [
        {**result, "url": normalize_serp_url(result.get("url", ""))}
        for result in serp_data.get("results", [])
    ]
    return data


def save_metadata(project_name: str, status: str) -> None:
    file_path = Path("research") / project_name / "metadata.json"
    data = json.loads(file_path.read_text(encoding="utf-8"))
    data["project_name"] = project_name
    data["status"] = status
    file_path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


def get_report_id(project_name: str) -> str:
    metadata = load_project_file(project_name, "metadata.json")
    metadata_id = str(metadata.get("id", "")).strip()
    return metadata_id or f"rr_{project_name}"


def get_canonical_serp_intent_evidence_ids(serp_intent_evidence: list[dict]) -> list[str]:
    canonical_attributes = {"dominant_intent", "mixed_intent"}
    return [
        item["evidence_id"]
        for item in serp_intent_evidence
        if item.get("claim", {}).get("attribute") in canonical_attributes
    ]


def run(project_name: str) -> None:
    keyword_data = load_keyword(project_name)
    print("=== Research Agent ===\n")
    print(f"Keyword  : {keyword_data['keyword']}")
    print(f"Language : {keyword_data['language']}")
    print(f"Country  : {keyword_data['country']}")

    report_id = get_report_id(project_name)

    query_intent_analysis = classify_query_intent(keyword_data["keyword"])
    save_project_file_if_changed(project_name, QUERY_INTENT_ANALYSIS_FILE, query_intent_analysis)
    query_intent_evidence = build_query_intent_evidence(query_intent_analysis, report_id=report_id)
    save_project_file_if_changed(project_name, QUERY_INTENT_EVIDENCE_FILE, query_intent_evidence)

    metrics_file = Path("research") / project_name / SEARCH_METRICS_FILE
    if metrics_file.exists():
        print("Using existing search metrics.")
        metrics = load_project_file(project_name, SEARCH_METRICS_FILE)
    else:
        print("Fetching search metrics...")
        metrics = get_provider().get_metrics(
            keyword=keyword_data["keyword"], language=keyword_data["language"], country=keyword_data["country"]
        )
    save_project_file_if_changed(project_name, SEARCH_METRICS_FILE, metrics)

    serp_file = Path("research") / project_name / SERP_ANALYSIS_FILE
    if serp_file.exists():
        print("Using existing SERP data.")
        serp_results = load_project_file(project_name, SERP_ANALYSIS_FILE)
    else:
        print("Fetching SERP data...")
        serp_results = get_serp_provider().get_results(
            keyword=keyword_data["keyword"], language=keyword_data["language"], country=keyword_data["country"]
        )
    serp_results = canonicalize_serp_results(serp_results)
    save_project_file_if_changed(project_name, SERP_ANALYSIS_FILE, serp_results)

    competitor_analysis = analyze_competitors(serp_results)
    save_project_file_if_changed(project_name, COMPETITOR_ANALYSIS_FILE, competitor_analysis)

    serp_intent_analysis = analyze_serp_intent(serp_results)
    save_project_file_if_changed(project_name, SERP_INTENT_ANALYSIS_FILE, serp_intent_analysis)
    serp_intent_evidence = build_serp_intent_evidence(serp_intent_analysis, report_id=report_id)
    save_project_file_if_changed(project_name, SERP_INTENT_EVIDENCE_FILE, serp_intent_evidence)

    intent_alignment_analysis = analyze_intent_alignment(query_intent_analysis, serp_intent_analysis)
    save_project_file_if_changed(project_name, INTENT_ALIGNMENT_ANALYSIS_FILE, intent_alignment_analysis)
    intent_alignment_evidence = build_intent_alignment_evidence(
        intent_alignment_analysis,
        report_id=report_id,
        query_intent_evidence_id=query_intent_evidence["evidence_id"],
        serp_intent_evidence_ids=get_canonical_serp_intent_evidence_ids(serp_intent_evidence),
    )
    save_project_file_if_changed(project_name, INTENT_ALIGNMENT_EVIDENCE_FILE, intent_alignment_evidence)

    serp_strategy_signal = analyze_serp_strategy_signal(intent_alignment_analysis)
    save_project_file_if_changed(project_name, SERP_STRATEGY_SIGNAL_FILE, serp_strategy_signal)
    serp_strategy_signal_evidence = build_serp_strategy_signal_evidence(
        serp_strategy_signal, report_id=report_id, intent_alignment_evidence_id=intent_alignment_evidence["evidence_id"]
    )
    save_project_file_if_changed(project_name, SERP_STRATEGY_SIGNAL_EVIDENCE_FILE, serp_strategy_signal_evidence)

    research_report = build_research_report(
        report_id=report_id,
        metadata=load_project_file(project_name, "metadata.json"),
        keyword=keyword_data,
        search_intent=query_intent_analysis,
        search_metrics=metrics,
        serp_analysis=serp_results,
        competitor_analysis=competitor_analysis,
        intent_evidence=(
            [query_intent_evidence]
            + serp_intent_evidence
            + [intent_alignment_evidence, serp_strategy_signal_evidence]
        ),
    )
    save_project_file_if_changed(project_name, RESEARCH_REPORT_FILE, research_report)

    print("\nUpdating metadata...")
    save_metadata(project_name, "research_started")
    print("Metadata updated.")


if __name__ == "__main__":
    run("expat-health-insurance")
