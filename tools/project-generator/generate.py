#!/usr/bin/env python3

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "tools/project-generator/config/modules.json"

FILES = {
    "modules/research/README.md": "# Research Engine\n",
    "modules/research/contracts/research-report.json": """{
  "keyword": "",
  "search_intent": "",
  "audience": "",
  "entities": [],
  "questions": [],
  "competitors": [],
  "sources": [],
  "content_gaps": [],
  "recommended_article_type": "",
  "status": "draft"
}
""",
    "modules/research/schema/report.schema.json": """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Research Report",
  "type": "object"
}
""",
    "modules/research/pipeline/workflow.md": "# Research Workflow\n",
    "modules/research/examples/example.json": """{
  "keyword": "best expat health insurance"
}
""",
    "modules/research/validation/validation-rules.json": """{
  "required": [
    "keyword",
    "search_intent",
    "sources"
  ]
}
"""
}

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def create_directories(config):
    for module in config["modules"]:
        base = f"modules/{module['name']}"

        (ROOT / base).mkdir(parents=True, exist_ok=True)
        print(f"[DIR] {base}")

        for directory in module["directories"]:
            path = f"{base}/{directory}"
            (ROOT / path).mkdir(parents=True, exist_ok=True)
            print(f"[DIR] {path}")

    shared_dirs = [
        "shared/models",
        "shared/schemas",
        "shared/types",
        "shared/utils",
        "knowledge-vault",
        "docs",
        "tests"
    ]

    for directory in shared_dirs:
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
        print(f"[DIR] {directory}")

def create_files():
    for path, content in FILES.items():
        file_path = ROOT / path

        if not file_path.exists():
            file_path.write_text(content, encoding="utf-8")
            print(f"[FILE] {path}")
        else:
            print(f"[SKIP] {path}")


if __name__ == "__main__":
    print("IRL AI Core Project Generator")

    config = load_config()
    print(config)

    create_directories(config)
    create_files()

    print("Done.")
