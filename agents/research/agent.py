import json
from pathlib import Path

from connectors.keyword_metrics.provider import get_provider

SEARCH_METRICS_FILE = "search-metrics.json"

def load_keyword(project_name: str) -> dict:
    """
    Load keyword.json from a research project.
    """

    file_path = Path("research") / project_name / "keyword.json"

    return json.loads(file_path.read_text(encoding="utf-8"))

def save_json(path, data):
    """
    Save a dictionary as JSON.
    """

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
        )

def save_project_file(project_name: str, filename: str, data: dict) -> None:
    """
    Save a JSON file inside a research project.
    """

    path = Path("research") / project_name / filename
    save_json(path, data)

def load_project_file(project_name: str, filename: str) -> dict:
    """
    Load a JSON file from a research project.
    """

    path = Path("research") / project_name / filename

    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

def save_project_file_if_changed(
    project_name: str,
    filename: str,
    data: dict,
) -> None:
    """
    Save a project file only if its content has changed.
    """

    current_data = load_project_file(project_name, filename)

    if current_data != data:
        save_project_file(project_name, filename, data)

def save_metadata(project_name: str, status: str) -> None:
    """
    Update metadata.json for the project.
    """

    file_path = Path("research") / project_name / "metadata.json"

    data = json.loads(file_path.read_text(encoding="utf-8"))

    data["project_name"] = project_name
    data["status"] = status

    file_path.write_text(
        json.dumps(data, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

def run(project_name: str) -> None:
    """
    Execute the Research Agent.
    """

    keyword_data = load_keyword(project_name)

    print("=== Research Agent ===")
    print()

    print(f"Keyword  : {keyword_data['keyword']}")
    print(f"Language : {keyword_data['language']}")
    print(f"Country  : {keyword_data['country']}")

    provider = get_provider()

    metrics = provider.get_metrics(
    keyword=keyword_data["keyword"],
    language=keyword_data["language"],
    country=keyword_data["country"],
)

    save_project_file_if_changed(
    project_name,
    SEARCH_METRICS_FILE,
    metrics,
)
    
    print()
    print("Updating metadata...")

    save_metadata(project_name, "research_started")

    print("Metadata updated.")

if __name__ == "__main__":

    run("expat-health-insurance")