import json
from pathlib import Path


def load_keyword(project_name: str) -> dict:
    """
    Load keyword.json from a research project.
    """

    file_path = Path("research") / project_name / "keyword.json"

    return json.loads(file_path.read_text(encoding="utf-8"))

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

    print()
    print("Updating metadata...")

    save_metadata(project_name, "research_started")

    print("Metadata updated.")

if __name__ == "__main__":

    run("expat-health-insurance")