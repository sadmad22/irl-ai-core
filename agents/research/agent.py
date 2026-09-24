import json
from pathlib import Path

from .connectors.keyword_metrics.base import validate_keyword_metrics_response
from .connectors.keyword_metrics.provider import get_provider
from .connectors.serp.base import validate_serp_response
from .connectors.serp.normalization import normalize_serp_url
from .connectors.serp.provider import get_provider as get_serp_provider
from .analyzers.competitor import analyze_competitors
from .analyzers.entity import analyze_entities
from .analyzers.question import analyze_questions
from .analyzers.business import analyze_business
from .analyzers.authority import analyze_authority
from .analyzers.intent_alignment import analyze_intent_alignment
from .analyzers.serp_strategy_signal import analyze_serp_strategy_signal
from .analyzers.query_intent import classify_query_intent
from .analyzers.serp_intent import analyze_serp_intent
from .evidence.query_intent import build_query_intent_evidence
from .evidence.serp_intent import build_serp_intent_evidence
from .evidence.intent_alignment import build_intent_alignment_evidence
from .evidence.serp_strategy_signal import build_serp_strategy_signal_evidence
from .evidence.entity import build_entity_evidence
from .evidence.question import build_question_evidence
from .evidence.business import build_business_evidence
from .evidence.authority import build_authority_evidence
from .evidence.substantive import SOURCE_MATERIAL_FILE, SUBSTANTIVE_EVIDENCE_FILE, build_substantive_evidence_from_file
from .evidence.passage_bound import (
    PASSAGE_BOUND_SOURCE_MATERIAL_FILE,
    build_canonical_evidence_from_file,
)
from .source_corpus import SOURCE_URLS_FILE, build_source_corpus_from_file
from .report import build_research_report
from .recommendation_runner import run_recommendation_from_report
from .decision_runner import run_decision_from_report
from .content_strategy_runner import run_content_strategy_from_report

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
ENTITY_ANALYSIS_FILE = "entity-analysis.json"
ENTITY_EVIDENCE_FILE = "entity-evidence.json"
QUESTION_ANALYSIS_FILE = "question-analysis.json"
QUESTION_EVIDENCE_FILE = "question-evidence.json"
BUSINESS_ANALYSIS_FILE = "business-analysis.json"
BUSINESS_EVIDENCE_FILE = "business-evidence.json"
AUTHORITY_ANALYSIS_FILE = "authority-analysis.json"
AUTHORITY_EVIDENCE_FILE = "authority-evidence.json"
SUBSTANTIVE_RESEARCH_SOURCE_FILE = SOURCE_MATERIAL_FILE
SUBSTANTIVE_EVIDENCE_OUTPUT_FILE = SUBSTANTIVE_EVIDENCE_FILE
RESEARCH_REPORT_FILE = "research-report.json"
RECOMMENDATION_FILE = "recommendation.json"
DECISION_FILE = "decision.json"
CONTENT_STRATEGY_FILE = "content-strategy.json"


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


def save_project_file_if_changed(project_name: str, filename: str, data):
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


def build_substantive_evidence_for_project(*, report_id: str, project_path: Path) -> list[dict]:
    """Select the canonical substantive Evidence producer for the project state.

    Passage-bound material is authoritative whenever present. If it is absent,
    the legacy source-material path remains available for pre-E projects.
    """
    if (project_path / PASSAGE_BOUND_SOURCE_MATERIAL_FILE).exists():
        return build_canonical_evidence_from_file(
            report_id=report_id,
            project_path=project_path,
        )
    return build_substantive_evidence_from_file(
        report_id=report_id,
        project_path=project_path,
    )


def _source(project_name: str, artifact: str) -> dict:
    return {"type": "research_artifact", "project": project_name, "artifact": artifact}


def _provenance(analyzer: str, method: str) -> dict:
    return {"analyzer": analyzer, "method": method, "version": "v1"}


def run(project_name: str) -> None:
    keyword_data = load_keyword(project_name)