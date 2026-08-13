import json
from pathlib import Path
import sys

SCHEMA_VERSION = "https://json-schema.org/draft/2020-12/schema"

PARSER_DIR = Path(__file__).parent
sys.path.insert(0, str(PARSER_DIR))

from parser import parse_model

def build_properties(fields):

    properties = {}

    for field in fields:

        properties[field["field"]] = {
            "type": field["type"],
            "description": field["description"]
        }

    return properties


def build_required(fields):

    required = []

    for field in fields:

        if field["required"].lower() == "yes":
            required.append(field["field"])

    return required


def build_schema(model):

    fields = model["fields"]

    schema = {
        "$schema": SCHEMA_VERSION,
        "title": model["title"],
        "type": "object",
        "properties": build_properties(fields),
        "required": build_required(fields)
    }

    return schema

def write_schema(schema, path: Path):

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(schema, indent=2),
        encoding="utf-8"
    )

def generate_all_schemas():

    models_dir = Path("shared/models")
    schemas_dir = Path("shared/schemas")

    for model_path in models_dir.glob("*.md"):

        model = parse_model(model_path)

        schema = build_schema(model)

        schema_name = model_path.stem + ".schema.json"

        output_path = schemas_dir / schema_name

        write_schema(schema, output_path)

        print(f"[SCHEMA] {output_path}")

if __name__ == "__main__":

    model_path = Path("shared/models/keyword.md")

    model = parse_model(model_path)

    schema = build_schema(model)

    output_path = Path("shared/schemas/keyword.schema.json")

    write_schema(schema, output_path)

    print(f"Schema written to: {output_path}")