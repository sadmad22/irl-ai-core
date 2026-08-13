"""
Project Generator

Creates a new IRL AI Core research project from the shared JSON Schemas.

Workflow:

shared/schemas/*.schema.json
            │
            ▼
    initialize_from_schema()
            │
            ▼
 create_project_files()
            │
            ▼
research/<project>/
"""

import json
from pathlib import Path


SCHEMAS_DIR = Path("shared/schemas")
RESEARCH_DIR = Path("research")


def create_project(project_name: str) -> Path:
    """
    Create a new research project directory.

    Args:
        project_name: Project folder name.

    Returns:
        Path to the created project directory.
    """

    project_dir = RESEARCH_DIR / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    return project_dir


def initialize_from_schema(schema_path: Path) -> dict:
    """
    Build an empty JSON document from a JSON Schema.

    Args:
        schema_path: Path to a *.schema.json file.

    Returns:
        Dictionary containing default values for every property.
    """

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    defaults = {}

    for field, info in schema["properties"].items():

        field_type = info["type"]

        if field_type == "string":
            defaults[field] = ""

        elif field_type == "integer":
            defaults[field] = 0

        elif field_type == "number":
            defaults[field] = 0

        elif field_type == "boolean":
            defaults[field] = False

        elif field_type == "array":
            defaults[field] = []

        elif field_type == "object":
            defaults[field] = {}

        else:
            defaults[field] = None

    return defaults


def create_project_files(project_dir: Path) -> None:
    """
    Create one JSON file for every schema.

    Args:
        project_dir: Target project directory.
    """

    for schema_file in SCHEMAS_DIR.glob("*.schema.json"):

        filename = schema_file.stem.replace(".schema", "") + ".json"

        file_path = project_dir / filename

        data = initialize_from_schema(schema_file)

        file_path.write_text(
            json.dumps(
                data,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )


def generate_project(
    project_name: str,
    keyword: str,
    language: str,
    country: str
) -> Path:
    """
    Generate a complete research project.

    Args:
        project_name: Project name.

    Returns:
        Path to the generated project.
    """

    project_dir = create_project(project_name)

    create_project_files(project_dir)

    keyword_file = project_dir / "keyword.json"

    data = json.loads(keyword_file.read_text(encoding="utf-8"))

    data["keyword"] = keyword
    data["language"] = language
    data["country"] = country

    keyword_file.write_text(
    json.dumps(data, indent=4, ensure_ascii=False),
    encoding="utf-8"
)

    return project_dir


if __name__ == "__main__":

    project = generate_project(
    project_name="expat-health-insurance",
    keyword="expat health insurance",
    language="en",
    country="US"
)

    print(f"Project created: {project}")