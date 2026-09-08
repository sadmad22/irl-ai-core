import json
from pathlib import Path


def test_production_orchestrator_schema_locks_stage_order_and_lifecycle():
    schema = json.loads(Path("shared/schemas/production-orchestrator.schema.json").read_text(encoding="utf-8"))
    props = schema["properties"]

    assert props["schema_version"]["const"] == "1.0"
    assert props["lifecycle_stage"]["enum"] == ["running", "completed", "failed"]
    assert props["current_stage"]["enum"] == [
        "research", "intelligence", "configuration", "structure", "draft",
        "editorial_cleanup", "media", "linking", "optimization", "qa",
        "article_package", None,
    ]
    assert props["article_package"]["type"] == ["object", "null"]
    assert props["error"]["type"] == ["object", "null"]
